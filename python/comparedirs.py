#! /usr/bin/env python3

from   collections import defaultdict
from   typing import DefaultDict, Tuple
import os
import shelve

from   lib.files import get_hash, walk, PathList


# Types
class FileInfo(object):
    def __init__(self, path: str, mtime: int, size: int):
        self.path  = path
        self.mtime = mtime
        self.size  = size
        self.hash  = None if size else "0"


    def __repr__(self):
        return "<%s('%s')>" % (self.__class__.__name__, self.path)


class DirInfo(object):
    def __init__(self):
        # List of FileInfos in this directory
        self.files   = []

        # dict(dirpath: [(left_file_path, right_file_path) that matched])
        self.matches = defaultdict(list)


class Comparison(object):
    """ Holds a description of a path comparison. See files, folders, sizes, hashes. """
    DB = "C:\\temp\\hashes.db"

    def __init__(self):
        self.files   = {}                   # Dict[str, FileInfo]
        self.folders = defaultdict(DirInfo) # DefaultDict[str, DirInfo]
        self.sizes   = defaultdict(list)    # DefaultDict[int, List[str]]
        self.hashes  = defaultdict(list)    # DefaultDict[str, List[FileInfo]]
        self.cache_hit = 0
        self.cache_miss = 0
        self.matches = None


    def scan(self, paths: PathList, excludes: PathList = None) -> None:
        """
        Scans the given directory paths for files to consider for matching.

        :param paths: Iterable that provides paths to scan for folders/files.
        :param excludes: Optional iterable that specifies folder names or absolute paths to ignore.
        """
        # Local name imports/aliases
        from os.path import dirname

        if self.files:
            self.__init__()     # Calling scan resets values

        folders, files, sizes = self.folders, self.files, self.sizes

        for file_path, mtime, size in walk(paths, excludes):
            file_info = FileInfo(file_path, mtime, size)
            files[file_path] = file_info

            if size > 0:
                folders[dirname(file_path)].files.append(file_info)
                sizes[size].append(file_info)

        # Only sizes with > 1 file have anything worth comparing
        self.sizes = dict((sz, files) for sz, files in self.sizes.items() if len(files) > 1)


    def _purge(self, percentage=100.):
        """ Testing Helper: nuke a percentage of DB contents """
        with shelve.open(self.DB) as db:
            if percentage < 100.:
                from random import sample
                for kill in sample(list(db.keys()), int(len(db.keys()) * (percentage/100.))):
                    db[kill] = None
            else:
                db.clear()
                db.sync()


    def match(self, readcallback=None, filecallback=None) -> Tuple[int, int]:
        """
        Retrieves hashes for all the files found to populate self.matches

        :return: total files that matched, discrete files
        """
        if not self.files:
            raise ValueError("No files found (did you call scan?)")

        with shelve.open(self.DB) as db:
            for size, files in sorted(self.sizes.items()):
                chunk_size = size if not readcallback else 8 * 4096
                for file_info in files:
                    if file_info.hash:
                        if readcallback:
                            readcallback(file_info.path, size, size, 0)
                        if filecallback:
                            filecallback(file_info)
                        continue
                    dbinf = db.get(file_info.path, None)
                    if not dbinf or dbinf.mtime != file_info.mtime or dbinf.size != size:
                        file_info.hash = get_hash(file_info.path, size, readcallback, chunk_size)
                        db[file_info.path] = file_info
                        self.cache_miss += 1
                    else:
                        file_info.hash = dbinf.hash
                        if readcallback:
                            readcallback(file_info.path, size, size, 0)
                        self.cache_hit  += 1
                    self.hashes[file_info.hash].append(file_info)
                    if filecallback:
                        filecallback(file_info)

        self.matches = {hash_str: infos for hash_str, infos in self.hashes.items() if len(infos) > 1}
        
        return sum(len(h) for h in self.matches.values()), len(self.matches)


def main(paths: PathList, excludes: PathList = None):
    
    comparison = Comparison()

    comparison.scan(paths=paths, excludes=excludes)
    print("Folders:", len(comparison.folders))
    print("Files  :", len(comparison.files))
    print("Sizes  :", len(comparison.sizes))

    comparison.hash()


if __name__ == "__main__":
    main(paths=("G:\\",), excludes=(".svn", ".git", "G:\\SEM"))
