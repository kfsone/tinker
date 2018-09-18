import logging
import os
import re
from stat import S_ISDIR, S_ISREG

from dirwalker import directory_walker
from entities import DirectoryEntity, FileEntity
from sftpsession import SFTPSession


class Inventory(object):
    ROOT_PATH        = '.'
    REMOTE_INVENTORY = "remote"
    LOCAL_INVENTORY  = "local"


    def __init__(self, source_type, path, filter_pattern=None):
        self.source_type = source_type
        self.path        = path.replace('\\', '/')
        self.filter_re   = re.compile(filter_pattern)
        # content will be dict(relative-path: Entity), the first entry
        # has to be the root aka '.'
        self.content     = {
            self.ROOT_PATH: DirectoryEntity(self.ROOT_PATH, None, None),
        }


    def populate(self, logger):
        raise NotImplementedError()


    def add(self, parent, name, stat_info, logger):
        """
        Creates and adds an appropriate Entity for an item to the inventory under parent.

        Uses 'stat_info' to determine if the file is a directory or a file, and if a file,
        what it's size (st_size) and last-modified (st_mtime) values are.

        :param parent:  The ancestor (directory) that contains the item,
        :param name:    The 'basename' of the item (it its filename in its parent folder),
        :param stat_info: Either None or an object that meeds the st_mode requirements for S_ISDIR,
                        otherwise a stat-like buffer with st_size and st_mtime.

        :return:        Relative path of the object if it was added and not filtered.
        """
        
        assert isinstance(parent, DirectoryEntity)
        relative_path = os.path.normpath(parent.name + os.sep + name).replace('\\', '/')
        if self.filter_re and self.filter_re.match(relative_path):
            logger.debug("excluding %s", relative_path)
            return None

        # Create the appropriate entity object
        if S_ISREG(stat_info.st_mode):
            logger.debug(" > + %s s:%d m:%d", name, stat_info.st_size, stat_info.st_mtime)
            entity = FileEntity(name, parent.name, stat_info)
        elif S_ISDIR:
            logger.debug(" > + %s/", name)
            entity = DirectoryEntity(relative_path, parent.name, stat_info)
        else:
            logger.info(" X '%s' is not a file/directory, ignoring", name)

        # Add to the actual inventory itself
        self.content[relative_path] = entity
        parent.contents.append(entity)

        return relative_path


    # Helpers:
    def __getitem__(self, key):         return self.content[key]
    def get(self, key, default=None):   return self.content.get(key, default)
    def __len__(self):                  return len(self.content)
    def __contains__(self, key):        return key in self.content
    def __delitem__(self, key):         del self.content[key]
    def __iter__(self):                 return iter(self.content)
    def keys(self):                     return self.content.keys()
    def values(self):                   return self.content.keys()
    def items(self):                    return self.content.items()
    def iterkeys(self):                 return self.content.iterkeys()
    def iteritems(self):                return self.content.iteritems()
    def itervalues(self):               return self.content.itervalues()


class RemoteInventory(Inventory):
    def __init__(self, remote_host, remote_path, username, password, filter_pattern=None):
        super(RemoteInventory, self).__init__(self.REMOTE_INVENTORY, remote_path, filter_pattern)
        self.hostname = remote_host
        self.username = username
        self.password = password


    def populate(self, logger):
        """
        Get an inventory of files in/below a path on a remote host via sftp.

        NOTE: Paths will have '/' separators on all platforms.
        """

        # Open an SSH session with an sftp connection over it.
        sftp = SFTPSession(self.hostname, self.username, self.password, self.path, logger=logger)

        # sftp provides several functions for listing directories, but
        # there's no direct equivalent for "os.walk". So we create a
        # working list of directories to be processed and iterate over
        # that, adding new directories as we go.
        logger.note("Getting remote inventory %s:%s", self.hostname, self.path)
        paths = ['.']
        add, content = self.add, self.content
        while paths:
            subdir, paths = paths[0], paths[1:]
            directory = content[subdir]
            logger.info(" > %s", subdir)
            assert isinstance(directory, DirectoryEntity)
            for attrs in sftp.client.listdir_iter(subdir):
                rel_path = add(directory, str(attrs.filename), attrs, logger)
                if rel_path and S_ISDIR(attrs.st_mode):
                    paths.append(rel_path)

        logger.info("Remote inventory: %d items", len(self))

        # close the sftp session.
        sftp.close()


class LocalInventory(Inventory):
    def __init__(self, local_path, filter_pattern=None):
        super(LocalInventory, self).__init__(self.LOCAL_INVENTORY, local_path, filter_pattern)


    def populate(self, logger):
        """
        Get an inventory of files in/below a local path using os.walk.

        NOTE: Paths will have '/' separators on all platforms.
        """

        logger.note("Getting local inventory: %s", self.path)

        # Walk the directory tree top-down
        add, content = self.add, self.content
        for path, dirs, files in directory_walker(self.path):

            # Translate the absolute path to a '/'-separated, relative-path
            rel_path = os.path.relpath(path, self.path).replace('\\', '/')

            logger.debug(" > %s", rel_path)
            directory = content[rel_path]

            # Add entries for all of our subdirectories. While this may
            # look weird, I'm trying to avoid making assumptions about
            # order in which we get things. It won't hurt perf too much.
            kept_dirs = []
            for dirent in dirs:
                if add(directory, dirent[0], dirent[1], logger):
                    kept_dirs.append(dirent)

            # Optimization: The dirs variable is mutable, allowing us to tell
            # the os.walk which directories to skip.
            if len(kept_dirs) != len(dirs):
                dirs[:] = kept_dirs

            # Now iterate over all the files and find the ones we can
            # stat. Anything we can't stat, we're basically going to ignore.
            for fileent in files:
                add(directory, fileent[0], fileent[1], logger)


