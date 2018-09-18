# Entity types used by sync.

import os


class Entity(object):
    """ Simple base class for Directory/File/Symlink etc """
    def __init__(self, name, parent, stat_buf):
        self.name   = name
        self.parent = parent
        self.size   = stat_buf.st_size if stat_buf else 0
        self.mtime  = stat_buf.st_mtime if stat_buf else 0

    def __repr__(self):
        return "<%s(%s)>" % (self.__class__.__name__, self.name)

    def differs(self, rhs):
        return self.name != rhs.name


class DirectoryEntity(Entity):
    """ Represents a directory """
    def __init__(self, name, parent, stat_buf):
        assert not name.endswith('/')
        super(DirectoryEntity, self).__init__(name, parent, stat_buf)
        self.contents = []


class FileEntity(Entity):
    """ Represents a file """
    def __init__(self, name, parent, stat_buf):
        super(FileEntity, self).__init__(name, parent, stat_buf)
        self.md5sum = None

    def differs(self, rhs):
        if self.size != rhs.size or self.mtime != rhs.mtime:
            return True
        return super(FileEntity, self).differs(rhs)


###TODO: "Target" could be tricky, but do we care?
#class SymlinkEntity(Entity):
#   """ Represents a symlink """
#   def __init__(self, name, target):
#       self.name, self.target = name, target


