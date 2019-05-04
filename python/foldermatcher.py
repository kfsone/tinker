#! /usr/bin/env python3

import os
import yaml

from collections import Counter
from hashlib import sha512
from itertools import chain
from os.path import join as pathjoin

from typing import (Callable, Dict, List, Tuple)

try:
    from nose import tools
except ImportError:
    pass

class DirInfo(str):
    pass

def dir_entry(dirname) -> DirInfo:
    """ Formats a directory name for hashing """
    dirname = dirname if isinstance(dirname, str) else pathjoin(*dirname)
    return DirInfo(f"{dirname}\x00")

def file_entry(filename: str, size: int) -> DirInfo:
    """ Formats a filename and its size for hashing """
    filename = filename if isinstance(filename, str) else pathjoin(*filename)
    return DirInfo(f"{filename}\x01{size}\x02")


def note(*args, **kwargs):
    print("--", *args, **kwargs)


class DirEntryMock:
    """ For simulating 'DirectoryEntry' objects as returned by scandir 
    >>> de = DirEntryMock(pathjoin("folder"), "file", 11135)
    >>> os.path.split(de.path)
    ('folder', 'file')
    >>> de.name
    'file'
    >>> de.stat().st_size
    11135
    >>> de.is_dir(), de.is_file()
    (False, True)
    >>> de = DirEntryMock(pathjoin("folder"), "sub", 0)
    >>> de.is_dir(), de.is_file()
    (True, False)
    """
    def is_dir(self): return self.st_size == 0
    def is_file(self): return self.st_size != 0
    def __init__(self, path, name, size):
        self.path = pathjoin(path, name)
        self.name = name
        self.st_size = size
    def stat(self):
        return self
    def __repr__(self):
        return f"<DirEntryMock(path={self.path}, name={self.name}, size={self.st_size}, d={self.is_dir()}, f={self.is_file()})>"


def build_content_table(folder: str, scandir: Callable=os.scandir) -> Dict[str, List[DirInfo]]:
    """ Produce a relatively flat dictionary of a directory try: {path: [*_entry] } """
    content_table = {}
    # Walk the directory tree and collate the content of every folder into that folder's entry.
    todo = [os.path.normpath(folder)]
    while todo:
        path = todo.pop()
        content = []
        for dirent in scandir(path):
            if dirent.is_dir():
                todo.append(dirent.path)
                content.append(dir_entry(dirent.name))
            elif dirent.is_file():
                content.append(file_entry(dirent.name, dirent.stat().st_size))
        content_table[path] = sorted(content)

    return content_table


def mock_scandir(content):
    content = yaml.load(content)
    def scandir_fn(path):
        folder = content
        for component in path.split(os.sep):
            folder = folder[component]
        for item, contents in folder.items():
            if isinstance(contents, int):
                yield DirEntryMock(path, item, contents)
            else:
                yield DirEntryMock(path, item, 0)
    return scandir_fn


def test_build_content_table():

    scandir = mock_scandir(".: {}")
    tools.eq_(build_content_table(".", scandir), {".":[]})

    scandir = mock_scandir(".:\n d1: {}")
    tools.eq_(build_content_table(".", scandir), {".":[dir_entry("d1")], pathjoin(".", "d1"): []})

    scandir = mock_scandir("""
        .:
            f1: 123
            d1:
                f2: 234
    """)
    expected = {".":[dir_entry("d1"), file_entry("f1", 123)], pathjoin(".", "d1"): [file_entry("f2", 234)]}
    tools.eq_(build_content_table(".", scandir), expected)


def coalesce_folder_content(content_table: Dict[str, List[DirInfo]]) -> Dict[str, List[DirInfo]]:
    """
    Propagate the content of every folder up into its parent folders.
    
    >>> result = coalesce_folder_content({"top": ["file1", "dir1"], pathjoin("top", "dir1"): ["file2"]})
    >>> [os.path.split(p) for p in sorted(result['top'])]
    [('', 'dir1'), ('dir1', 'file2'), ('', 'file1')]
    >>> result[pathjoin('top', 'dir1')]
    ['file2']
    """

    modified = set()
    for path in reversed(sorted(content_table.keys())):
        content = content_table[path]
        if not content:
            continue
        parent = os.path.dirname(path)
        parent_content = content_table.get(parent)
        if parent_content is not None:
            my_name = os.path.basename(path)
            parent_content.extend(os.path.join(my_name, ent) for ent in content)
            modified.add(parent)

    for path in modified:
        content_table[path].sort()

    return content_table


def mutation_check(source, changes={}):
    expected = dict(source)
    if changes:
        expected.update(changes)

    result = coalesce_folder_content(dict(source))

    tools.eq_(result.keys(), expected.keys())
    tools.eq_(result, expected)


def test_coalesce_folder_content_empty():
    mutation_check({}, None)
    mutation_check({".":[]}, None)
    mutation_check({".":["d1"], "d1":[]}, None)
    mutation_check({".":["d1", "d2"], "d1":[], "d2":[]}, None)


def test_build_and_coalesce():
    def run_content(content):
        scandir = mock_scandir(content)
        content_table = build_content_table(".", scandir)
        return coalesce_folder_content(content_table)

    result = run_content(".: {}")
    tools.eq_(result, {".":[]})

    result = run_content("""
        .:
            d1:
                m1: 100
                s1:
                    m2: 200
        """)
    tools.eq_(result["."], [dir_entry("d1"), file_entry(("d1", "m1"), 100), dir_entry(("d1", "s1")), file_entry(("d1", "s1", "m2"), 200)])


def test_coalesce_folder_content_non_empty():
    mutation_check({
            ".":[file_entry("f1", 111), dir_entry("d1")],
            pathjoin(".", "d1"):[file_entry("f2", 111)]
    }, {
        ".": sorted([file_entry("f1", 111), dir_entry("d1"), file_entry(("d1", "f2"), 111)])
    })

    mutation_check({
            ".":[dir_entry("d1"), dir_entry("d2")],
            pathjoin(".", "d1"):[file_entry("f1", 123)],
            pathjoin(".", "d2"):[file_entry("f2", 234)],
    }, {
        ".": sorted([dir_entry("d1"), dir_entry("d2"), file_entry(("d1", "f1"), 123), file_entry(("d2", "f2"), 234)])
    })

    mutation_check({
            ".": [dir_entry("d1")],
            pathjoin(".", "d1"):[dir_entry("d2")],
            pathjoin(".", "d1", "d2"):[file_entry("f1", 333)],
    }, {
        ".": sorted([dir_entry("d1"), dir_entry(("d1", "d2")), file_entry(("d1", "d2", "f1"), 333)]),
        pathjoin(".", "d1"): sorted([dir_entry("d2"), file_entry(("d2", "f1"), 333)])
    })


def hash_all(content_table: Dict[str, List[str]]) -> Dict[str, Tuple[str]]:
    hash_to_folders = {}
    for path, content in content_table.items():
        if content:
            hashed = sha512("".join(content).encode()).hexdigest()
            hash_to_folders[hashed] = hash_to_folders.get(hashed, ()) + (path,)
    return hash_to_folders

def test_hash_all():
    as_hash = lambda x: sha512(x.encode()).hexdigest()
    tools.eq_(hash_all({}), {})
    tools.eq_(hash_all({"key": "value"}), {as_hash("value"): ("key",)})
    tools.eq_(hash_all({"key1": "value", "key2": "value"}), {as_hash("value"): ("key1","key2")})
    tools.eq_(hash_all({"key1": "val1", "key2": "val2"}), {as_hash("val1"): ("key1",), as_hash("val2"): ("key2",)})


def get_matches(hash_to_folders: Dict[str, List[str]]):
    def parents(p):
        while True:
            p = os.path.dirname(p)
            if not p: break
            yield p

    # Generate a list of all the paths that were listed as matching at least one other hash
    matching_paths = set(chain.from_iterable(folders for folders in hash_to_folders.values() if len(folders) > 1))
    matching_paths = set(p for p in matching_paths if not (set(parents(p)) & matching_paths) )

    # Now cull hashes to only those with matches in the matching paths list.
    matches = {hash_val: [f for f in folders if f in matching_paths] for hash_val, folders in hash_to_folders.items()}
    matches = {hash_val: folders for hash_val, folders in matches.items() if len(folders) > 1}

    return matches, matching_paths


def test_get_matches():
    tools.eq_(get_matches({}), ({}, set()))
    tools.eq_(get_matches({"hash1": []}), ({}, set()))
    tools.eq_(get_matches({"hash1": ["e1"]}), ({}, set()))
    tools.eq_(get_matches({"hash1": ["e1", "e2"]}), ({"hash1": ["e1", "e2"]}, {"e1","e2"}))
    tools.eq_(get_matches({"hash1": ["e1", "e2"], "hash2": [pathjoin("e1", "ea"), pathjoin("e2", "ea")], "hash3": ["e3", "e4"]}), ({"hash1": ["e1", "e2"], "hash3": ["e3", "e4"]}, {"e1","e2","e3","e4"}))


def get_colliding_hashes(path):
    # Get a table of folder: contents
    content_table = build_content_table(path)
    note(f"{len(content_table)} folders")

    # Percolate the contents of sub-folders up into their parents
    content_table = coalesce_folder_content(content_table)

    # Hash the results
    hash_to_folders = hash_all(content_table)
    note(f"{len(hash_to_folders)} hashes")

    # Narrow to colliding hashes
    matches, matching_paths = get_matches(hash_to_folders)
    note(f"{len(matches)} collide")
    note(f"{len(matching_paths)} colliding paths")

    for h, folders in matches.items():
        yield folders

if __name__ == "__main__":
    for matching_folders in get_colliding_hashes("G:\\Wispa\\Oliver"):
        common = os.path.commonpath(matching_folders)
        print(f"| {common}")
        for folder in matching_folders:
            print(f"| + {os.path.relpath(folder, common)}")
        print()
