#! /usr/bin/python
#
##############################################################################
#
# Directory walker - Copyright (C) Oliver 'kfsone' Smith 2017
#
# BLURB
#   Tired of using 'du -s * | sort -n | tail' to find what is using up all your
#   disk space? Too much on your disk for a graphical tool to be useful?
#
# DESCRIPTION
#   'Walker' class provides a way to analyze disk usage of a directory tree.
#   Primarily intended for inspection in an interaction Python session, such
#   as ipython, ipython notebook, or just plain python. It also has a simple
#   'main' so that it can be used as a command.
#
# EXAMPLE
#
#   Command line:
#       walk.py ${HOME}
#
#   Interactive:
#
#     import walk
#     w = 
#
#   Code:
#
#     from __future__ import print_function
#     from walk import Walker
#
#     # Constructing a Walker object causes it to walk the tree and build
#     # a model of the directory structure.
#     #  Walker.root    := object representing the top of the tree,
#     #  Walker.files   := unsorted list(file nodes)
#
#     walk = Walker(".")  # reads current directory.
#
#     # Sort the file list by size and show me the biggest and smallest.
#     walk.files.sort(key=lambda f: f.size, reverse=True)
#     print("{:12n} {:s}".format(walk.files[0].size, walk.files[0].path))
#     print("{:12n} {:s}".format(walk.files[-1].size, walk.files[-1].path))
#
#     # Walk the directory tree in size order.
#     dt = walk.root
#     while True:
#         print("{:12n} {:s}".format(dt.size, dt.path))
#         if not dt.children:
#             break
#         dt = dt[0]
#
#     # Summarize what's using space at the second level:
#     d.root[0].describe(fh=sys.stdout)  # default behavior
#
#     # Descend the largest part of the directory tree.
#     for f in d.files:
#         # stop when we encounter a file < 60% of the first file's size
#         if f.size < d.files[0].size * 0.60:
#             break
#         print("{:12n} {:s}".format(f.size, f.path))
#


from __future__ import print_function

import json
import os
import os.path
import sys

from stat import S_ISREG


##############################################################################
# Base class for representing an on-disk entity (file or directory).
#

class Entity(object):
    """ Base class for File and Directory nodes. """

    def __init__(self, parent, name, size=0):
        if name is None:
            raise ValueError("'name' is None.")
        self._parent = parent
        self._name   = name
        self._size   = size
        if parent:
            parent._children.append(self)

    def describe(self, file=sys.stdout):
        """ Simple description of an entity. """
        print(self.path, self._size, file=fh)

    @property
    def parent(self):
        """ The parent entity (or None for the Root node). """
        return self._parent

    @property
    def path(self):
        """ Returns the full path of an Entity. """
        pathname = self._name
        parent   = self._parent
        join     = os.path.join
        while parent:
            pathname = join(parent._name, pathname)
            parent   = parent._parent
        return pathname

    @property
    def size(self):
        """ Entity's size in bytes. """
        return self._size

    def __str__(self):
        return "{:15,}Kb {:s}".format(int(self._size / 1024), self.path)


##############################################################################
# Representation of a Directory: Differs from 'File' in that it can
# contain more Entitys.
#
class Directory(Entity):

    def __init__(self, parent, name):
        super(Directory, self).__init__(parent, name)
        if self.__class__.__name__ != "Root" and parent is None:
            raise ValueError("Only 'Root' can have parent==None")
        self._children = []     # Items below me
        self._sorted   = False  # If the child list is sorted.


    def toJSON(self, minsize):
        dir = {
            'dir':       (self._name, self._size),
            'contains':  [
                    c.toJSON(minsize) for c in self.children
                    if c._size >= minsize
            ]
        }
        if self._children and not dir['contains']:
            dir['contains'].append(self.children[0].toJSON(minsize))
        return dir


    def describe(self, percentile=0, min_size=0, fh=sys.stdout):
        """ Reports the contents of this directory. """
        print("{:s}/ ({:,}):".format(self.path, self.size), file=fh)
        children = self.children
        if not children:
            return
        maxSizeLen = len("{:,}".format(children[0]._size))
        sizeCutoff = max(float(self._children[0]._size) * float(percentile),
                        min_size)
        for child in self._children:
            if child._size < sizeCutoff:
                break
            print("    {size:{maxSz},} {name:s}".format(maxSz=maxSizeLen,
                        name=child._name, size=child._size),
                    file=fh)

    @property
    def children(self):
        """
            A size-ordered list of immediate children of this Directory,
            files and directories. Lazy sorted in descending size order
            on first access. i.e. self.children[0] is the largest
            Directory or File in this Directory.
        """
        if not self._sorted:
            self._children.sort(key=lambda c: c._size, reverse=True)
            self._children = tuple(self._children)
            self._sorted = True
        return self._children

    @property
    def files(self):
        """ The list of files in this directory. """
        return self._files

    def __getitem__(self, index):
        """ Array-like short-cut for self.children[index] """
        return self.children[index]

    def __repr__(self):
        fmt = "<Directory(%s, %s, %d)>"
        return fmt % (self._parent.path, self._name, self._size)


class Root(Directory):
    def __init__(self, name):
        super(Root, self).__init__(None, name)

    def __repr__(self):
        return "<Root(%s, %d)>" % (self._name, self._size)


##############################################################################
# Representation of a File: Differs from 'Directory' in that it can't have
# any descendents.
#
class File(Entity):
    children = []   # Barren: no need for a property.

    def __init__(self, parent, name, size, links):
        if not size:
            raise ValueError("Empty file should be ignored.")
        super(File, self).__init__(parent, name, size)

    def __repr__(self):
        return "<File(%s, %s, %d)>" % (self._parent.path, self._name,
                self._size)

    def toJSON(self, minsize):
        return (self._name, self._size)


##############################################################################
# Walker class itself.
#
class Walker(object):

    @property
    def root(self):
        """ The top-level Directory of the directory walk. """
        return self._root

    @property
    def files(self):
        """ A flat, unsorted list of all the files that were scanned. """
        return self._files


    @property
    def size(self):
        """
            Returns the total size of the directory tree.
            Equivalent to self.root.size.
        """
        return self._root._size


    def __init__(self, top_dir):
        """
            Collect disk-usage information for a directory by recursively
            accumulating the file and directory information below it.

            The top-level Directory node is exposed as '.root' which you
            can use to walk the tree, and the complete list of distinct
            files (excluding symlinks and hardlinks) is provided as
            '.files' - unsorted by default.

            Last, but not least, '.size' provides the total size of
            the directory tree.

            \param   top_dir     Directory to begin descending from.
        """

        while top_dir.endswith('/'):
            top_dir = top_dir[:-1]

        if not os.path.isdir(top_dir):
            raise ValueError("'%s' is not a directory." % top_dir)

        # If this fails, user can catch the error directly.
        rootStat = os.stat(top_dir)
        rootDev  = rootStat.st_dev

        allFiles, allDirs, hardLinks, accessErrors = [], {}, set(), False

        self._root = Root(name=top_dir)
        allDirs[top_dir] = self._root

        # Walk through all the directories from path down.
        for (path, dirs, files) in os.walk(top_dir):

            pathEntity = allDirs[path]      # Find the node for this path.
            basePath   = path + '/'         # Reduce the number of adds
            sizes      = 0                  # Accumulate this path's sizes here

            for filename in files:

                try:
                    stat = os.stat(basePath + filename)
                except:
                    accessErrors = True
                    continue

                # Ignore zero-sized files, they contribute nothing.
                size = stat.st_size
                if size == 0:
                    continue
                # Don't cross devices.
                if stat.st_dev != rootDev:
                    continue
                # Only include a linked file's size once.
                if stat.st_nlink:
                    if stat.st_ino in hardLinks:
                        # We've seen this inode before.
                        continue
                    hardLinks.add(stat.st_ino)
                if not S_ISREG(stat.st_mode):
                    # Not a regular file
                    continue

                sizes += size
                entity = File(pathEntity, filename, size, True)

            # Add all the children to the parent directory, rather than
            # adding them individually. This works because we handle
            # directories *after* files.
            allFiles.extend(pathEntity._children)

            # Add directory descendants
            for name in dirs:
                allDirs[basePath + name] = Directory(pathEntity, name)

            # Propogate sizes upwards
            while pathEntity:
                pathEntity._size += sizes
                pathEntity = pathEntity._parent

        self._files = allFiles


    def toJSON(self, min_pctg=0):

        minsize = self.root.size * min_pctg
        return json.dumps(self.root.toJSON(minsize))


if __name__ == "__main__":

    from argparse import ArgumentParser

    parser = ArgumentParser('walker')
    parser.add_argument('--json', default=False, action='store_true',
            help='Serialize the resulting tree as json')
    parser.add_argument('--pctg', default=0, type=float,
            help='Only show files >= this percent of the disk usage')
    parser.add_argument('path', default='.', type=str, nargs='?',
            help='Which directory to walk (default is .)')
    args = parser.parse_args(sys.argv[1:])

    # Crude demonstration of how to use the Walker class.

    walker = Walker(args.path)

    # Just dump the result as json
    if args.json:
        if args.pctg < 0 > args.pctg > 100:
            raise ValueError("--pctg must be between 0 and 100")
        print(walker.toJSON(args.pctg / 100.))
        sys.exit(0)

    files = walker.files
    files.sort(key=lambda f: f.size, reverse=True)

    print("Scanned %d files under %s" % (len(files), args.path))
    print()
    print("10 largest files:")

    for i in range(0, min(len(files), 10)):
        print("{:15,}Kb {:s}".format(int(files[i].size / 1024), files[i].path))
    print()

    # Walk the directory tree culling lists of items that are atleast
    # 75% the size of the total disk usage, and building a list of
    # those nodes.
    #
    # When we reach a leaf (a node that has nothing > 75%), take the
    # top 3 children: this covers the case where one directory takes
    # up 75% of the disk with N much smaller files.
    #
    stack, minsize = [walker.root], walker.root.size * 0.75
    entities = [walker.root]
    while stack:
        entity = stack.pop()
        selected = [e for e in entity.children if e.size >= minsize]
        stack.extend(selected)
        if not selected:
            selected = entity.children[:3]
        entities.extend(selected)

    # Size order, please.
    entities.sort(key=lambda e: e.size, reverse=True)

    print("Paths containing the most data:")
    for entity in entities:
        print("{:15,}Kb {:s}".format(int(entity.size / 1024), entity.path))


