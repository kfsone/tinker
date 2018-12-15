#! /usr/bin/env python3

import argparse
from   dataclasses import dataclass
import hashlib
import mmap
import os
from   paramiko import SFTPAttributes
import posixpath
import re
import shutil
from   stat import S_IFDIR, S_IFLNK, S_IFREG, S_ISDIR, S_ISLNK, S_ISREG
import sys
import threading
import time
from   typing import Any, Callable, Dict, List, Tuple, Union

from   sync.sftpsession import SSHSession, SFTPSession
from   sync.worker      import Worker

from   lib import loggingex
import logging

logger = logging.getLogger("sync")

DEFAULT_LOG_LEVEL = logging.WARNING

TRASH_FOLDER = ".SyncTrash"


@dataclass
class DownloadItem:
    path:  str
    name:  str
    size:  int
    mtime: int


def is_dir(attrs) -> bool:
    return S_ISDIR(attrs.st_mode)

def is_file(attrs) -> bool:
    return S_ISREG(attrs.st_mode)

def is_symlink(attrs):
    return S_ISLNK(attrs.st_mode)


def dry_check(dry_run: bool, function: Any, args: Union[List[Any], None]=None, kwargs: Union[Dict[str, Any], None]=None, rval: Any=None):
    """ Execute a function call if this is not a dry-run, otherwise report what we would have done instead. """
    
    if args is None: args = ()
    if kwargs is None: kwargs = {}
    if dry_run:
        logger.info("WhatIf: %s(args=%s, kwargs=%s)", function.__name__, args, kwargs)
        return rval
    else:
        logger.spam("doing: %s(args=%s, kwargs=%s)", function.__name__, args, kwargs)
        return function(*args, **kwargs)


yamlcmt   = re.compile('^\s*[;#]').match

class ArgParseWithYamlFromFile(argparse.ArgumentParser):

    def convert_arg_line_to_args(self, arg_line):
        arg_line = arg_line.strip()
        if yamlcmt(arg_line):
            return ()
        l, _, r = arg_line.partition(' ')
        return (l,) if not r else (l, r)


def initialize_trash(config: argparse.Namespace):
    # Delete any existing trash bin and then create a new one.
    if os.path.exists(config.trash_path):
        logger.info("Removing previous %s", config.trash_path)
        dry_check(config.dry_run, shutil.rmtree, (config.trash_path,))


def parse_arguments(arglist):
    parser = ArgParseWithYamlFromFile("syncer", fromfile_prefix_chars='@')

    parser.add_argument("--username", required=True,
                    help="Login name for the remote host")
    parser.add_argument("--password", required=True,
                    help="Password for the remote host")
    parser.add_argument("--exclude", "-x", dest="exclude", action="append", default=[],
                    help="Don't include anything matching these regexs")
    parser.add_argument("--no-mtime", dest="use_mtime", default=True, action="store_false",
                    help="Don't compare mtimes for determining file changes")
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

    config = parser.parse_args(arglist)

    # Validation/normalization of arguments.
    if not os.access(config.local, os.R_OK):
        raise ValueError("Local path is not accessible: %s" % config.local)
    if not os.access(config.local, os.W_OK):
        raise ValueError("Local path is not writable: %s" % config.local)

    config.exclude    = re.compile('|'.join(config.exclude + [TRASH_FOLDER]))

    config.trash_path = os.path.normpath(os.path.join(config.local, TRASH_FOLDER))
    initialize_trash(config)

    # Check we can connect to the remote host:
#    try:
#        ssh = SSHSession(config.remote, config.username, config.password)
#    except as e:
#        raise RuntimeError("Cannot open SSH connection to '%s': %s" % (
#                config.remote, str(e))

#    rc = ssh.execute("python summer.py 0 summer.py")
#    if rc is not 0:
#        raise RuntimeError("Failed executing 'summer.py' on remote host.")
#    ssh.close()

    return config


def create_dir(config, rel_path, name, mtime):
    full_path = os.path.normpath(os.path.join(config.local, rel_path, name))
    if os.path.exists(full_path):
        shutil.rmtree(full_path)
    os.makedirs(full_path)
    touch(config.local, posixpath.join(rel_path, name), mtime)
    logger.info("Created: %s", full_path)


def create_file(local_path: str, name: str, size: int, mtime: int, callback=None, dry_run: bool=False):
    """
    Create a file with a given initial size and optionally call a callback with the file object of
    the file while it is open during creation (e.g. so you can write to it).

    :param local_path str: Path to the folder in which the file will be created,
    :param name str: Target name of the file to be created (.tmp is added during creation and then it is renamed)
    :param size int: Size of the file in bytes
    :param mtime int: Specifies a modified time to give the file
    :param callback: Callable that takes a file handle and returns the resulting size of the file
    :return: Size of the file created (incase callback changed it)
    """
    if not os.path.exists(local_path):
        dry_check(dry_run, os.makedirs, (local_path,))

    full_path = os.path.normpath(os.path.join(local_path, name))

    if dry_run:
        logger.info("WhatIf: create file %s, %d bytes", full_path, size)
        if callback:
            size = callback(sys.stderr)
    else:
        tmp_path  = full_path + ".tmp"
        with open(tmp_path, "wb") as fl:
            fl.truncate(size)
            if callback:
                size = callback(fl)
        try:
            os.unlink(full_path)
        except:
            pass
        os.rename(tmp_path, full_path)

    dry_check(dry_run, os.utime, (full_path, (mtime, mtime)))

    logger.debug("Created %s (size %d, mtime %d)", full_path, size, mtime)

    return size


def move_to_trash(config: argparse.Namespace, rel_path: str, deleted_items, dry_run=False):
    """
    Move items from the local path to the sync trash bin, a safe delete.
    """

    if not deleted_items:
        logger.debug("No items to delete.")
        return

    trash_path = os.path.normpath(os.path.join(config.trash_path, rel_path))
    dry_check(dry_run, os.makedirs, (trash_path,))

    local_path = os.path.normpath(os.path.join(config.local, rel_path))

    for item in deleted_items:
        src = os.path.join(local_path, item)
        dst = os.path.join(trash_path, item)
        assert src != dst
        dry_check(dry_run, os.renames, (src, dst))
        logger.spam("Moved %s to %s", src, TRASH_FOLDER)

    logger.info("%d items moved to %s.", len(deleted_items), trash_path)


def touch(root, rel_path, mtime=None):
    """ Update the modified time of a file """
    mtime = (mtime, mtime) if mtime else None
    os.utime(os.path.normpath(os.path.join(root, rel_path)), mtime)


def get_remote_files(sftp: SFTPSession, rel_path: str):
    logger.debug("remote: %s", rel_path)
    return {
        str(attrs.filename): attrs
        for attrs in sftp.client.listdir_iter(rel_path)
        if not is_symlink(attrs)
    }


def get_local_files(root: str, rel_path: str,
                    normalize=os.path.normpath, joinpath=os.path.join):
    local_path = normalize(joinpath(root, rel_path))
    logger.debug("local: %s", local_path)
    try:
        generator = os.scandir(local_path)
    except FileNotFoundError:
        return {}
    return {
        ent.name: SFTPAttributes.from_stat(ent.stat(follow_symlinks=False), ent.name)
        for ent in generator
        if not ent.is_symlink()
    }


def filtered(rel_path, stats, exclude_re):
    match = exclude_re.match
    join = posixpath.join
    return {
            k: e for k, e in stats.items()
            if not match(join(rel_path, k))
    }


def get_path_deltas(rel_path, config, sftp, sum_worker, dl_worker):

    remote_stats = filtered(rel_path, get_remote_files(sftp, rel_path), config.exclude)
    logger.spam("%s: remote_stats: %s", rel_path, remote_stats)

    children     = list(posixpath.join(rel_path, n) for n, st in remote_stats.items() if is_dir(st))

    local_stats  = filtered(rel_path, get_local_files(config.local, rel_path), config.exclude)
    logger.spam("%s: local_stats: %s", rel_path, local_stats)

    remote_set   = set(remote_stats.keys())
    local_set    = set(local_stats.keys())
    logger.spam("%s: remotes: %s, locals: %s", rel_path, remote_set, local_set)

    added        = remote_set - local_set
    removed      = local_set  - remote_set
    persisted    = remote_set - (added | removed)

    logger.spam("%s: added: %s, removed: %s, persisted: %s", rel_path, added, removed, persisted)

    need_sum     = []

    for name in persisted:
        lhs, rhs = remote_stats[name], local_stats[name]
        lhs_file, rhs_file = is_file(lhs), is_file(rhs)

        # If the entity type changes, e.g File->Dir, we need to delete the
        # local entry and add the item to both the 'removed' and 'added'
        # lists.
        if lhs_file != rhs_file:
            removed.add(name)
            added.add(name)
            continue

        # If size changes, ignore on directories but force download files.
        if lhs_file and lhs.st_size != rhs.st_size:
            dl_worker.put(DownloadItem(rel_path, name, lhs.st_size, lhs.st_mtime))
            continue

        # If the mtime changes, for a file, check the MD5 sum, for a dir,
        # just touch the mtime on that folder.
        if lhs.st_mtime != rhs.st_mtime:
            if lhs_file:
                need_sum.append(lhs)
            else:
                dry_check(config.dry_run, touch, (config.local, os.path.join(rel_path, name), lhs.st_mtime))

    if need_sum:
        sum_worker.put((rel_path, need_sum))

    return {k: remote_stats[k] for k in added}, removed, children


def sum_work(config: argparse.Namespace, client: SSHSession, data: Tuple[str, List[SFTPAttributes]], nextq: Worker) -> None:
    # data is a tuple(relative path, list(FileEntity))
    rel_path, need_sum = data
    info = { str(e.filename): (e.st_size, e.st_mtime) for e in need_sum }

    # Issue a remote md5sum command for just the files
    filenames = "\0".join(e.filename for e in need_sum) + "\0"
    cmd = "cd '%s' && xargs -0 md5sum --binary" % (posixpath.join(config.remote, rel_path))

    logger.info("Fetching %d remote checksums", len(filenames))
    logger.debug(cmd)

    rc, stdout = client.execute(cmd, read_stdout=True, inputs=filenames)
    if rc is not 0:
        raise RuntimeError("md5sum failed: %d" % rc)

    hashes = {}
    for line in stdout.decode().split("\n"):
        if not line: continue
        checksum, _, filename = line.partition(" *")
        hashes[filename] = checksum.lower()

    for filename, remote_hash in hashes.items():
        filepath = posixpath.join(rel_path, filename)

        fullpath = os.path.normpath(os.path.join(config.local, filepath))
        with open(fullpath, "rb") as fh:
            mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            local_hash = hashlib.md5(mm).hexdigest().lower()
            mm.close()

        if local_hash != remote_hash:
            logger.info("%s: remote:%s, local:%s", filepath, remote_hash, local_hash)
            nextq.put(DownloadItem(rel_path, filename, *info[filename]))
        else:
            mtime = info[filename][1]
            logger.debug("Hash match for %s -> touching %d", filepath, mtime)
            touch(config.local, filepath, mtime)


def dl_progress(filename: str, bytes_dl: int, bytes_ttl: int) -> None:
    logger.info("%s: {:9n}/{:9n}".format(filename, bytes_dl, bytes_ttl))
    

def dl_work(config: argparse.Namespace, sftp: SFTPSession, data: DownloadItem, nextq: Worker) -> None:
    rel_path = posixpath.join(data.path, data.name)
    remote_path = posixpath.join(config.remote, rel_path)
    logger.info("Downloading %s (%.2fKb)", remote_path, data.size / 1024)
    if config.dry_run:
        return

    local_path = os.path.join(config.local, data.path)
    sized = create_file(local_path, data.name, data.size, data.mtime, callback=lambda fl:
                            sftp.client.getfo(remote_path, fl,
                                        lambda dl, ttl: dl_progress(rel_path, dl, ttl))
    )
    logger.debug("Downloaded %d bytes", sized)


def main(config: argparse.Namespace):

    # Create a worker for downloading individual files
    dl_client   = SFTPSession(config.host, config.username, config.password, initial_path=config.remote, logger=logger)
    dl_worker   = Worker(config, dl_work, dl_client, None, logger=logger)
    dl_worker.start()

    # For lists of changed files we need to perform checksums on
    sum_client  = SSHSession(config.host, config.username, config.password, logger=logger)
    sum_worker  = Worker(config, sum_work, sum_client, dl_worker, logger=logger)
    sum_worker.start()

    # We'll need an sftp session to get directory listings.
    sftp = SFTPSession(config.host, config.username, config.password, initial_path=config.remote, logger=logger)

    # Paths that we need to inspect.
    dir_queue  = ['']

    try:
        while dir_queue:

            rel_path = dir_queue.pop(0)
            logging.info('~ %s', rel_path)
            added, removed, children = get_path_deltas(rel_path, config, sftp, sum_worker, dl_worker)

            # Remove anything that needs deleting first, so that if we have items that
            # changed type (e.g a file became a folder), we delete it before trying to
            # create anything. Also ensures we free up space where possible before adding
            # to usage.
            if removed:
                move_to_trash(config, rel_path, removed, config.dry_run)

            # Now add things.
            for name, remote_stat in added.items():
                if is_file(remote_stat):
                    dl_worker.put(DownloadItem(rel_path, name, remote_stat.st_size, remote_stat.st_mtime))
                else:
                    dry_check(config.dry_run, create_dir, args=(config, rel_path, name, remote_stat.st_mtime))

            # If this gave us child directories, add them.
            dir_queue.extend(children)

    finally:
        logger.debug("Closing workers")
        sum_worker.close()
        logger.debug("Finished")


if __name__ == "__main__":
    config = parse_arguments(sys.argv[1:])
    logger.debug("config: %s", config)

    # For each --verbose/-v lower the logging level by one priority
    log_level = loggingex.get_relative_level(DEFAULT_LOG_LEVEL, -config.verbose)
    logging.basicConfig(level=log_level)
    logger.setLevel(log_level)

    main(config)
