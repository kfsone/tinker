#! /usr/bin/env python3

from collections import defaultdict, deque
import hashlib
import mmap
from   mmap import ACCESS_READ
import itertools
import os
from os import scandir
from typing import DefaultDict, Dict, Iterable, List, NamedTuple, Tuple
import shelve


PathList = Iterable[str]


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
    DB = "C:\\temp\\hashes.db"
    SYNC_RATE = 500

    def __init__(self):
        self.files   = {}                   # Dict[str, FileInfo]
        self.folders = defaultdict(DirInfo) # DefaultDict[str, DirInfo]
        self.sizes   = defaultdict(list)    # DefaultDict[int, List[str]]
        self.hashes  = defaultdict(list)    # DefaultDict[str, List[FileInfo]]
        self.cache_hit = 0
        self.cache_miss = 0

    @property
    def matches(self) -> Iterable[Dict[str, List[FileInfo]]]:
        return {hash_str: infos for hash_str, infos in self.hashes.items() if len(infos) > 1}


    def scan(self, paths: PathList, excludes: PathList = None) -> None:
        self.__init__()

        # Local name imports/aliases
        from os.path import dirname

        folders, files, sizes = self.folders, self.files, self.sizes

        for file_path, mtime, size in walk(paths, excludes):
            file_info = FileInfo(file_path, mtime, size)
            files[file_path] = file_info

            if size > 0:
                folders[dirname(file_path)].files.append(file_info)
                sizes[size].append(file_info)

        # Only sizes with > 1 file have anything worth comparing
        self.sizes = dict((sz, files) for sz, files in self.sizes.items() if len(files) > 1)

    def get_all_files(self):
        files = deque()
        for size in sorted(self.sizes.keys()):
            for file_info in self.sizes[size]:
                if file_info.hash:
                    files.appendleft((size, file_info))
                else:
                    files.append((size, file_info))
        return files

    def purge(self, percentage=100.):
        with shelve.open(self.DB) as db:
            if percentage < 100.:
                from random import sample
                for kill in sample(list(db.keys()), int(len(db.keys()) * (percentage/100.)):
                    db[kill] = None
            else:
                db.clear()
                db.sync()

    def hash(self, readcallback=None, filecallback=None):
        with shelve.open(self.DB) as db:
            for size, file_info in self.get_all_files():
                chunk_size = size if not readcallback else 8 * 4096
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


def walk(paths: PathList, excludes: PathList = None) -> Iterable[os.DirEntry]:
    from os.path import abspath, normpath

    pending_paths = deque(abspath(p) for p in paths)

    # Normalize the list of excluded folders.
    excludes = excludes or ()
    excludes = set(normpath(e) for e in excludes)

    while pending_paths:
        path = pending_paths.popleft()
        try:
            for dirent in scandir(path):
                if dirent.is_dir(follow_symlinks=False):
                    if excludes and (set((dirent.name, dirent.path)) & excludes):
                        continue
                    pending_paths.append(dirent.path)
                else:
                    stat = dirent.stat()
                    yield dirent.path, stat.st_mtime, stat.st_size
        except PermissionError as e:
            print(e)


def get_hash(file_path: str, size: int, callback=None, chunk_size=4*4096) -> str:
    with open(file_path, "rb") as fh:
        with mmap.mmap(fh.fileno(), size, access=ACCESS_READ) as mm:
            md5 = hashlib.md5()
            for start in range(0, size, chunk_size):
                remaining = size - start
                chunk = min(remaining, chunk_size)
                md5.update(mm[start:start+chunk])
                if callback:
                    callback(file_path, size, chunk, remaining - chunk)

            return "%s:%s" % (size, md5.hexdigest())


def main(paths: PathList, excludes: PathList = None):
    
    comparison = Comparison()

    comparison.scan(paths=paths, excludes=excludes)
    print("Folders:", len(comparison.folders))
    print("Files  :", len(comparison.files))
    print("Sizes  :", len(comparison.sizes))

    comparison.hash()

if __name__ == "__main__":
    main(paths=("G:\\",), excludes=(".svn", ".git", "G:\\SEM"))
