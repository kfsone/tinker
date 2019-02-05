#! /usr/bin/env python3

from collections import defaultdict
import os
from tempfile import gettempdir


class Constants:        # namespace

    STAT_PATH       =   ".cd.stat"


class FileInfo(object):

    def __init__(self, stat_result):
        self.mtime = stat_result.st_mtime
        self.size  = stat_result.st_size


def main(paths, excludes=()):
    """ this is main """

    folders, files = {}, {}
    size_index = dict(list)

    from os import stat, walk
    from os.path import abspath, join as joinpath, normpath

    absnorm = lambda path: abspath(normpath(path))

    excludes = set(absnorm(e) for e in excludes)

    tempdir = joinpath(absnorm(gettempdir()), Constants.STAT_PATH)
    excludes.add(tempdir)

    for path in paths:

        for curpath, dirs, filenames in walk(path, followlinks=False):

            for d in dirs:
                dir_path = joinpath(curpath, d)
                if d not in excludes and dir_path not in excludes:
                    folders[dir_path] = list()

            for f in filenames:
                file_path = joinpath(curpath, f)
                stat_result = stat(file_path)
                files[file_path] = FileInfo(stat_result)
                size_index[stat_result.st_size].append(file_path)

    print("Folders:", len(folders))
    print("Files  :", len(files))
    print("Sizes  :", len(size_index))


if __name__ == "__main__":
    main(("G:\\",), ("G:\\SEM",))
