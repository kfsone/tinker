from __future__ import print_function

import argparse
from entities import Entity, FileEntity, DirectoryEntity
from inventories import RemoteInventory, LocalInventory
import os
import pickle
import sys
from sftpsession import SFTPSession

sys.path.append("..")
from lib import loggingex
import logging

logger = logging.getLogger("sync")

DEFAULT_LOG_LEVEL = logging.WARNING

TRASH_FOLDER = ".SyncTrash"


##############################################################################
# Code.
#

def fetch_inventory(name, instance):
    """
    Attempt to read a cached file list from a pickle file, or otherwise
    invoke the given lambda function to fetch the list from a lister.

    :param name: descriptive name of what we're fetching
    :param instance: a new inventory object to populate if not unpickling

    :return: an inventory of files.
    """

    filename = name + ".pickle"

    if os.path.exists(filename):
        logger.note("Loading %s from %s", name, filename)
        with open(filename, "rb") as fh:
            inventory = pickle.load(fh)
        return inventory

    instance.populate(logger=logger)

    logger.info("Writing %s data to %s", name, filename)
    try:
        with open(filename, "wb") as fh:
            pickle.dump(instance, fh)
    except Exception as e:
        os.unlink(filename)
        raise

    return instance


def get_inventories(argv):

    REMOTE_NAME = "remote"
    LOCAL_NAME  = "local"

    remote_inv = fetch_inventory(REMOTE_NAME, RemoteInventory(
                        argv.host, argv.remote,
                        argv.username, argv.password,
                        filter_pattern=argv.exclude,
    ))
    local_inv = fetch_inventory(LOCAL_NAME, LocalInventory(
                        argv.local,
                        filter_pattern=argv.exclude,
    ))

    return remote_inv, local_inv


def get_delta(source_inv, source_set, target_set):

    delta = source_set - target_set
    parents = [source_inv[i].parent for i in delta]

    return delta, parents


def get_modified_files(remote_inv, remote_set, local_inv, local_set):

    # Get the intersection of the two sets so we don't have
    # to scan everything.
    common_items = remote_set & local_set

    # for items that had content changes
    changed_content = []

    # for items that, e.g, changed from file->dir etc
    changed_type = []

    for item in common_items:
        remote_item = remote_inv[item]
        local_item  = local_inv[item]

        assert isinstance(remote_item, Entity)
        if not isinstance(remote_item, type(local_item)):
            changed_type.append(item)
            continue

        if isinstance(remote_item, FileEntity):
            if remote_item.mtime == local_item.mtime:
                if remote_item.size == local_item.size:
                    continue
            changed_content.append(item)

    return set(changed_content), set(changed_type)


def get_changes(remote_inv, remote_set, local_inv, local_set):

    additions = get_delta(remote_inv, remote_set, local_set)
    deletions = get_delta(local_inv, local_set, remote_set)
    modified  = get_modified_files(remote_inv, remote_set, local_inv, local_set)

    return additions, deletions, modified


def dry_check(dry_run, function, args=None, kwargs=None, rval=None):
    if args is None: args = ()
    if kwargs is None: kwargs = {}
    if dry_run:
        logger.info("WhatIf: %s(args=%s, kwargs=%s)", function.__name__, args, kwargs)
        return rval
    else:
        logger.spam("doing: %s(args=%s, kwargs=%s)", function.__name__, args, kwargs)
        return function(*args, **kwargs)


def trash_deletions(local_path, deleted_items, dry_run=False):
    """
    Move items from the local path to the sync trash bin, a safe delete.
    """

    if not deleted_items:
        logger.debug("No items to delete.")
        return

    # Delete any existing trash bin and then create a new one.
    trash_path = os.path.normpath(os.path.join(local_path, TRASH_FOLDER))
    if os.path.exists(trash_path):
        logger.info("Removing previous %s", trash_path)
        dry_check(dry_run, os.removedirs, (trash_path,))
    logger.info("Creating %s for %d deletions", trash_path, len(deleted_items))
    dry_check(dry_run, os.makedirs, (trash_path,))

    # Build a list of only the items whose folders aren't being moved.
    # e.g. if dir1/dir2 is being moved, we don't need to move dir1/dir2/f1.txt
    moves = {
        item for item in deleted_items if os.path.dirname(item) not in deleted_items
    }
    logger.debug("Don't need to move: %s", (deleted_items - moves))

    for item in moves:
        src = os.path.normpath(os.path.join(local_path, item))
        dst = os.path.normpath(os.path.join(trash_path, item))
        assert src != dst
        dry_check(dry_run, os.renames, (src, dst))
        logger.spam("Moved %s to %s", item, TRASH_FOLDER)

    logger.info("%d items moved to %s.", len(deleted_items), trash_path)


def create_folders(local_path, new_folders, remote_inv, dry_run=False):
    directories = 0

    # Sort the directories in reverse order so that we get children first.
    for directory in reversed(sorted(new_folders)):
        entity = remote_inv[directory]
        assert isinstance(entity, Entity)
        assert isinstance(entity, DirectoryEntity)

        full_path = os.path.normpath(os.path.join(local_path, directory))
        if not os.path.exists(full_path):
            dry_check(dry_run, os.makedirs, (full_path,))

        # Always change the mtime to match
        dry_check(dry_run, os.utime, (full_path, (entity.mtime, entity.mtime)))

        directories += 1

    logger.info("Created %d new folders", directories)


def create_file(entity, local_path, callback=None, dry_run=False):
    assert isinstance(entity, FileEntity)
    folder = os.path.normpath(os.path.join(local_path, entity.parent))
    if not os.path.exists(os.path.dirname(folder)):
        dry_check(dry_run, os.makedirs, (folder,))

    entity_path = entity.parent + '/' + entity.name
    full_path = os.path.join(local_path, entity_path)
    size = entity.size
    if dry_run:
        logger.info("WhatIf: create file %s, %d bytes", full_path, size)
        if callback:
            size = callback(entity_path, sys.stderr)
    else:
        with open(full_path, "wb") as fl:
            fl.truncate(entity.size)
            if callback:
                size = callback(entity_path, fl)

    dry_check(dry_run, os.utime, (full_path, entity.mtime, entity.mtime))

    logger.debug("Created %s (size %d, mtime %d)", full_path, size, entity.mtime)

    return size


def create_zero_files(local_path, entities, dry_run=False):
    for entity in entities:
        create_file(entity, local_path, dry_run=dry_run)


def test_checksums(remote_host, remote_user, remote_pass, remote_path, local_path, items, dry_run=False):
    #ssh_client = ssh_session(remote_host, remote_user, remote_pass)
    #ssh_client.execute("cd '%s'" % remote_path)
    #ssh_client.execute()

    return items


def download_files(host, username, password, remote_path, remote_inv, local_path, paths, dry_run=False):
    logger.info("Downloading %d files:", len(paths))

    # Open a new SFTP session for the transfer.
    session = SFTPSession(argv.host, argv.username, argv.password, argv.remote, logger=logger)

    total_bytes = 0
    for path in paths:

        entity = remote_inv[path]
        assert isinstance(entity, Entity)
        assert not isinstance(entity, DirectoryEntity)
        assert entity.size > 0

        actual_size = create_file(entity, local_path,
                        lambda path, fl: \
                            dry_check(dry_run, session.client.getfo, (path, fl), rval=entity.size),
                        dry_run=dry_run)

        total_bytes += actual_size

    logger.info("Downloaded %d bytes in %d files", total_bytes, len(paths))


def check_no_dirs(title, pathlist, remote_inv):
    for path in pathlist:
        if isinstance(remote_inv[path], DirectoryEntity):
            logger.critical("%s in %s is a directory.", path, title)
            raise RuntimeError("Bad juju")


def main(argv):

    remote_inv, local_inv = get_inventories(argv)
    remote_set = set(remote_inv.iterkeys())
    local_set  = set(local_inv.iterkeys())

    added, deleted, modified = get_changes(remote_inv, remote_set, local_inv, local_set)

    # added is (<entities>, <parent names>)
    added_items, added_parents = added
    # deleted is (<entities>, <parent names>)
    deleted_items, deletion_parents = deleted
    # modified is (<changed content entities>, <changed type entities>)
    modified_content, changed_type = modified

    if None in deletion_parents:
        raise ValueError("TLD appears to be deleted.")

    check_no_dirs("modified_content", modified_content, remote_inv)

    # Move deletions and items that changed their type out of the way
    trash_deletions(argv.local, deleted_items | changed_type, argv.dry_run)

    # Create folders that are missing
    new_folders = set(i for i in added_items | changed_type if isinstance(remote_inv[i], DirectoryEntity))
    create_folders(argv.local, new_folders, remote_inv, dry_run=argv.dry_run)

    new_files   = added_items - new_folders
    check_no_dirs("new_files", new_files, remote_inv)

    # Eliminate any zero-size files
    zero_entities = set(
        remote_inv[f] for f in (modified_content | new_files | changed_type) 
        if isinstance(remote_inv[f], FileEntity) and remote_inv[f].size == 0
    )
    create_zero_files(argv.local, zero_entities, dry_run=argv.dry_run)
    zero_files = set(os.path.normpath(os.path.join(argv.local, i.parent, i.name)) for i in zero_entities)

    # Files that had their size changed must have changed in some way.
    size_changed  = set(i for i in modified_content if remote_inv[i].size != local_inv[i].size) - zero_files
    check_no_dirs("size_changed", size_changed, remote_inv)
    mtime_changed = modified_content - (size_changed | zero_files)
    check_no_dirs("mtime_changed", mtime_changed, remote_inv)

    # Any files that are purely new, or are someone replacing a dir with a file, we have
    # to fetch those. Until we can do partial checksumming, we need to also fetch any
    # files whose size changed.
    must_fetch = (new_files | changed_type | size_changed) - (zero_files | new_folders)

    # Checksum files with modified mtimes to determine what needs changing.
    checksum_changes = test_checksums(argv.host, argv.username, argv.password, argv.remote, argv.local, mtime_changed, dry_run=argv.dry_run)

    must_fetch.update(checksum_changes)

    download_files(argv.host, argv.username, argv.password, argv.remote, remote_inv, argv.local, must_fetch, dry_run=argv.dry_run)


def parse_arguments(arglist):
    parser = argparse.ArgumentParser("sync")

    parser.add_argument("--username", required=True,
                    help="Login name for the remote host")
    parser.add_argument("--password", required=True,
                    help="Password for the remote host")
    parser.add_argument("--exclude", "-x", dest="exclude", action="append", default=[],
                    help="Don't include anything matching these regexs")
    parser.add_argument("--dry-run", "-n", "-WhatIf", dest="dry_run", action="store_true",
                    help="Enable dry-run mode")
    parser.add_argument("--verbose", "-v", action="count", default=0,
                    help="Enable additional logging output")
    parser.add_argument("host",
                    help="Name/address[/:port] of the remote host")
    parser.add_argument("remote",
                    help="Path on the remote host")
    parser.add_argument("local", type=os.path.normpath,
                    help="Path on the local host")

    argv = parser.parse_args(arglist)

    # Validation/normalization of arguments.
    if not os.access(argv.local, os.R_OK):
        raise ValueError("Local path is not accessible: %s" % argv.local)
    if not os.access(argv.local, os.W_OK):
        raise ValueError("Local path is not writable: %s" % argv.local)

    if argv.exclude:
        argv.exclude = '|'.join(argv.exclude + [TRASH_FOLDER])

    return argv


if __name__ == "__main__":

    argv = parse_arguments(sys.argv[1:])
    logger.debug("argv: %s", argv)

    # For each --verbose/-v lower the logging level by one priority
    log_level = loggingex.get_relative_level(DEFAULT_LOG_LEVEL, -argv.verbose)
    logging.basicConfig(level=log_level)
    logger.setLevel(log_level)

    main(argv)

