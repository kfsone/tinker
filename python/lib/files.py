#! /usr/bin/env python3

from   collections import deque
from   mmap import ACCESS_READ
from   os import scandir
from   typing import Iterable, Tuple
import hashlib
import mmap
import os


# Type aliases
PathList = Iterable[str]


def walk(paths: PathList, excludes: PathList = None) -> Iterable[Tuple[str, int, int]]:
    """ Iterate across a directory tree yielding non-exclude files. """
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


def get_hash(file_path: str, size: int, chunk_size=None, checksummer=hashlib.md5) -> str:
    """ Efficiently get the hash for a given file, prefixed with the size. """
    # One-shot reads if chunk_size is <= 0
    if not chunk_size or chunk_size < 0:
        chunk_size = size

    with open(file_path, "rb") as fh:
        with mmap.mmap(fh.fileno(), size, access=ACCESS_READ) as mm:
            checksum = checksummer()
            for start in range(0, size, chunk_size):
                remaining = size - start
                chunk = min(remaining, chunk_size)
                checksum.update(mm[start:start+chunk])

            return "%s:%s" % (size, checksum.hexdigest())
