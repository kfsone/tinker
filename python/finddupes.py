#! /usr/bin/env python
#
"""
Find Dupes - Copyright (C) Oliver 'kfsone' Smith Sep 2017

Searches across N paths for files that are duplicated.

Files are initially grouped by size and then hashing is performed across
size buckets. Files below 1k are simply raw compared. Larger files have the
first 64k hashed with sha256. Finally, files that are size+hash matches are
raw-compared 16k at a time in O(n log n) compares.
"""


import argparse
import hashlib
import logging
import os
import struct
import sys

from collections import defaultdict
from itertools import chain
from multiprocessing.pool import ThreadPool as Pool


# <= this size, file comparisons are just raw.
RAW_SIZE = 512

# Maximum size to read: 256k
MIN_SIZE = 32
MAX_READ = 64 * 1024


class FileInfo(object):
    """
    Simple container for file information, specifically the normalized
    path and the size from stat.
    """
    def __init__(self, path, stat):
        self.path, self.size = os.path.normpath(path), stat.st_size

    def __repr__(self):
        return "FileInfo('%s', %d)" % (self.path, self.size)


def find_files(folders):
    """ Generator: Yields all files from recursively descending all
        of the paths provided. No overlap check is provided so files
        may be yielded twice if your paths overlap.

        :param folders: iterable of one-or-more path name
    """

    for folder in folders:
        folder = os.path.normpath(os.path.abspath(folder))
        if not os.path.isdir(folder):
            logging.warning("No such file or directory: %s" % folder)
            continue

        logging.info("Scanning %s" % folder)
        num_files = 0

        for path, dirs, files in os.walk(folder):
            base = path + os.path.sep
            yield from map(base.__add__, files)
            num_files += len(files)

        logging.debug("=> %s: %d files" % (folder, num_files))


def get_file_info(path):
    """ If the file can be stat'd, returns a FileInfo. """
    try:            stat = os.stat(path)
    except IOError: return
    if stat.st_size > MIN_SIZE:
        return FileInfo(path, stat)


def hash_file(info):
    """
    Returns a hash for the given FileInfo. If the file is less than RAW_SIZE,
    this hash will be b'R' + binary content of the file; otherwise,
    yields a packed representation of the size in bytes followed by the sha512
    hash of the first < MAX_READ bytes of the file.

    This allows smaller files to be easily and directly compared; while the
    remaining files can be bucketed to reduce the number of direct compares
    required.
    """

    try:
        infh = open(info.path, 'rb')
    except IOError:
        return None

    read_size = min(info.size, MAX_READ)
    if read_size <= RAW_SIZE:
        return info, b'R' + infh.read(read_size)
    else:
        hasher = hashlib.sha512()
        hasher.update(infh.read(read_size))
        return info, struct.pack("Q", info.size) + hasher.digest()


def find_candidates(folders):
    """ Save file information and yield entries that may have matches,
        based on having the same size initially. """
    # Since we're IO based, we'll use a worker pool.
    pool            = Pool(8)
    # Total number of files we considered
    num_files       = 0
    # Dictionary of {size: list(FileInfo)} for size-bucketing.
    size_lists      = defaultdict(list)
    # Count files we read raw data rather than hashing.
    files_raw       = 0
    # Count files we hashed
    files_hashed    = 0

    # Identify all the files that have the same size, any 1-length lists
    # can be eliminated as unique files.
    #
    logging.info("building size dict")

    candidates = pool.imap_unordered(get_file_info, find_files(folders), chunksize=8)
    for info in (i for i in candidates if i):
        num_files += 1
        size_lists[info.size].append(info)

    # Eliminate the size-based unique files.
    num_candidates = sum(len(l) for l in size_lists.values() if len(l) > 1)
    matched_sizes = (l for l in size_lists.values() if len(l) > 1)

    logging.debug("files:%d, sizes: %d, hashing candidates: %d" % (
                    num_files, len(size_lists), num_candidates))

    logging.info("hashing files")
    # Stream the files thru the hashing algorithm to generate an iterable
    # of ( (info, hash) or None )
    #
    hashes = pool.imap_unordered(hash_file, chain.from_iterable(matched_sizes))
    # Filter out the Nones.
    hashes = (v for v in hashes if v)

    # Sort the infos into buckets based on hashes, this will produce the
    # list of files that should be compared with each other.
    buckets = defaultdict(list)
    for (info, key) in hashes:
        if key[0] == b'R': files_raw += 1
        else:              files_hashed += 1
        buckets[key].append(info)

    logging.debug('raw files: %d, hashed files: %d, num hashes: %d' % ((
                    files_raw, files_hashed, len(buckets))))

    # Now yield list(FileInfo) based on hash buckets
    yield from (infos for infos in buckets.values() if len(infos) > 1)


def compare_files(seed, candidates):
    """
    Reads 'seed' a chunk-at-a-time and compares that chunk with the same
    chunk from each file in 'candidates', eliminating files as they fail
    to match, until either all of 'seed' has been read and compared or
    there are no candidates remaining.

    :param seed:        FileInfo of the first file,
    :param candidates:  List of FileInfos of the files to be compared,
    :return:            list(FileInfo{2,}) of matched files or empty list,
    """

    lf = open(seed.path, 'rb')
    goal = seed.size
    candfs = ((i, open(i.path, 'rb')) for i in candidates)
    read = 0
    while candfs and read < goal:
        lbuf = lf.read(16384)
        read += len(lbuf)

        newcandfs = []
        for (i, f) in candfs:
            rbuf = f.read(len(lbuf))
            if rbuf == lbuf:
                newcandfs.append((i, f))
        candfs = newcandfs

    return list(t[0] for t in candfs)


def match_lists(folders, min_size=None, max_size=None):
    """
    Generator: Yields (size, list(filepath)) for lists of files. The list in
    each tuple will contain as many instances of the same data found across
    all of the folders.

    :param folders: iterable that produces directory names
    :param min_size: minimum size (in bytes) to consider
    :param max_size: maximum size (in bytes) to consider
    :return: tuple(size_in_bytes, list(filepaths))
    """

    raw_matches, hash_matches = 0, 0

    if min_size:
        logging.debug("min file size: {:,} bytes".format(min_size))
    if max_size:
        logging.debug("max file size: {:,} bytes".format(max_size))

    for sizelist in find_candidates(folders):

        size = sizelist[0].size
        if min_size and size < min_size:
            continue
        if max_size is not None and size > max_size:
            continue

        if size <= RAW_SIZE:
            # Files that were small enough that we used the content instead
            # of the hash, so we can tell they actually match.
            raw_matches += len(sizelist)
            logging.debug('%d raw matches of size %d' % (len(sizelist), size))

            yield (size, list(i.path for i in sizelist))
            continue

        hash_matches += len(sizelist)

        matched = set()
        groups = 0
        for idx in range(0, len(sizelist) - 1):
            info = sizelist[idx]
            if info in matched:
                continue
            matches = compare_files(info, (i for i in sizelist[idx + 1:]
                                           if i not in matched))
            if matches:
                matched.add(info)
                matched.update(matches)
                yield (size, list(i.path for i in ([info] + matches)))
                groups += 1

        logging.debug('size: %d, groups: %d, dupes: %d' % (size, groups, len(matched)))

    logging.debug('%d raw matches, %d hashed matches' % (raw_matches, hash_matches))


def parse_arguments(arglist):

    parser = argparse.ArgumentParser('finddupes')
    parser.add_argument('--verbose', '-v', action='count',
                        help='Increase output verbosity')
    parser.add_argument('--json', action='store_true',
                        help='Output in json format')
    parser.add_argument('--ge', type=int,
                        help='Only consider files >= this size.')
    parser.add_argument('--le', type=int,
                        help='Only consider files <= this size.')
    parser.add_argument('paths', nargs='+', type=str, default=[],
                        help='Specify which path to search.')

    return parser.parse_args(arglist)


if __name__ == "__main__":

    args = parse_arguments(sys.argv[1:])

    if not args.verbose:
        logLevel = logging.WARNING
    else:
        logLevel = logging.INFO if args.verbose == 1 else logging.DEBUG
    logging.basicConfig(level=logLevel, stream=sys.stderr)

    if args.json:
        import json

    paths = args.paths or ['.']
    matches = list(match_lists(paths, args.ge, args.le))

    if not matches:
        if args.verbose:
            logging.info("No duplicates found.")
    else:
        if args.json:
            print(json.dumps(matches))
        else:
            maxlen = max(len("{:,}".format(m[0])) for m in matches)
            for size, files in matches:
                print("{sz:{ml},} {fls}".format(ml=maxlen, sz=size,
                                                fls=','.join(files)))
