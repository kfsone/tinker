#! /usr/bin/env python
"""
Find Dupes - Copyright (C) Oliver 'kfsone' Smith Sep 2017

Searches across N paths for files that are duplicated.

Files are initially grouped by size and then hashing is performed across
size buckets. Files below 1k are simply raw compared. Larger files have the
first 64k hashed with sha256. Finally, files that are size+hash matches are
raw-compared 16k at a time in O(n log n) compares.
"""

from __future__ import print_function
from __future__ import unicode_literals


import argparse
import hashlib
import logging
import os
import struct
import sys

from collections import defaultdict
from itertools import chain
from multiprocessing.pool import ThreadPool as Pool


# -----------------------------------------------------------------------------
# Settings.
class Constants:

    # Pass each worker thread this many stat candidates at a time.
    STAT_CANDIDATE_CHUNKSIZE = 10

    # Pass each worker thread this many files to hash at a time.
    HASH_FILE_CHUNKSIZE = 8

    # Upto this size, we will just read the entire file rather than hashing.
    RAW_READ_BYTES = 4096

    # When we do read hash, we will only hash upto this many bytes. The chances
    # of collision should be low enough that it's worth doing the full compare.
    # The higher this is set, the more double-reading has to be done.
    HASH_READ_BYTES = 64 * 1024  # 64k

    # Read this many bytes from each file at a time while doing compare.
    # OGS: 2 pages at a time seems good.
    READ_CHUNK_SIZE = 4096 * 2


# -----------------------------------------------------------------------------
# Helper types.
#
class FileInfo(object):
    """
    Simple container for file information, specifically the normalized
    path and the size from stat.
    """

    def __init__(self, path, stat):
        self.path, self.size = os.path.normpath(path), stat.st_size


    def __repr__(self):
        return "FileInfo('%s', %d)" % (self.path, self.size)



class Candidate(object):
    """
    Describes a comparison candidate and tracks which other Candidates
    it has been matched againt, if any.
    """

    def __init__(self, fileinfo):
        self.fileinfo   = fileinfo
        self.fh         = safe_open(fileinfo.path)
        self.index      = None
        self.candidates = None


    def init(self, index, candidates):
        self.index      = index
        self.candidates = set(range(len(candidates))) - set((index,))


    def discount(self, lost, candidates):
        """
        Remove the 'lost' candidates from our candidate list, and then
        remove our remaining candidates from the candidate list of each
        lost node.

        :param lost: List of indexes we no-longer match,
        :param candidates:  list(Candidate) from which to untrack our matches
        """

        self.candidates -= lost
        remove_set = set(self.candidates)
        remove_set.add(self.index)
        for idx in lost:
            candidates[idx].candidates -= remove_set



# Cross-platform filesystem matching.
#
if sys.platform == "win32":

    def same_top_level(lhs, rhs):
        """ test if two files are on the same drive. """

        return os.path.splitdrive(lhs) == os.path.splitdrive(rhs)

else:

    def same_top_level(lhs, rhs):
        """ test if two files are in the same top-level directory. """

        if lhs.rfind(os.path.sep) == 0 and rhs.rfind(os.path.sep) == 0:
            return True
        lhs, rhs = lhs.partition(os.path.sep)[1], rhs.partition(os.path.sep)[1]
        return lhs == rhs


def safe_open(path):
    """ If the file can be opened, returns a file handle; otherwise None."""

    try:
        return open(path, 'rb')
    except (IOError, PermissionError, FileNotFoundError):
        return None


class Catalog(object):
    """
    For efficiently producing a list of files in a given set of directory
    hierarchies that have been proven have the exact same content.

    Files are first bucketed by size using os.walk and stat; files that have
    a unique size need never even be opened.

    Next files are bucketed by the combination of size plus either the contents
    of the first
    Duplicates are found by searching for files with exact size matches.
    Large files with size matches have their first, upto, 64Kb hashed to
    narrow down likely dupes, and then finally efficiently compare all
    potential matches.
    """

    def __init__(self, folders, min_size=None, max_size=None,
                 ignore_folders=None, verbosity=0,
                 threads=None, logger=logging):
        """
        Constructs the catalog but does not fetch any files yet.

        :param folders:   list(Paths/Drives) to search,
        :param min_size:  Require files >= this number of bytes,
        :param max_size:  Require files <= this number of bytes,
        :param ignore_folders:   Absolute folders to ignore,
        :param threads:   [opt] number of threads to use in the pool,
        :param logger:    [opt] logger to use,
        """

        if threads is None:
            threads = os.cpu_count()

        self.folders        = folders
        self.min_size       = min_size or 1
        self.max_size       = max_size or sys.maxsize
        self.verbosity      = verbosity if verbosity and verbosity > 0 else 0
        self.ignore_folders = set(
            os.path.abspath(os.path.normpath(p)) for p in ignore_folders or []
        )
        self.logger         = logger
        self.files_observed = 0
        self.pool           = Pool(threads)


    def _get_files(self):
        """
        Generator: Yields all files from recursively descending all
        of the paths provided. No overlap check is provided so files
        may be yielded twice if your paths overlap.
        """

        self.files_observed = 0

        num_folders = 0

        for folder in self.folders:
            folder = os.path.normpath(os.path.abspath(folder))
            if not os.path.isdir(folder):
                self.logger.warning("No such file or directory: %s" % folder)
                continue

            self.logger.info("Scanning %s" % folder)
            num_folders += 1

            num_files = 0
            for path, dirs, files in os.walk(folder):
                if path in self.ignore_folders:
                    if self.verbosity:
                        self.logger.info('Ignoring %s' % path)
                    dirs[:] = []
                    continue
                if self.verbosity > 1:
                    self.logger.debug('Path %s' % path)

                base = path + os.path.sep
                yield from map(base.__add__, files)
                self.files_observed += len(files)
                num_files += len(files)

            if self.verbosity:
                self.logger.debug("=> %s: %d files" % (folder, num_files))

        if not num_folders:
            self.logger.error("No folders found to scan.")


        self.logger.debug("=> considered %d files" % self.files_observed)


    def _get_file_info(self, path):
        """
        Returns a FileInfo if the file can be stat'd and meets our size
        constraints.otherwise None.
        """

        try:
            stat = os.stat(path)
        except IOError:
            pass
        else:
            if self.min_size <= stat.st_size <= self.max_size:
                return FileInfo(path, stat)

        return None


    def _hash_file(self, info):
        """
        Returns data used to provide a reasonably high probability of
        distinguishing distinct files.

        For files < Constants.RAW_READ_BYTES, we just go ahead and read
        that many bytes; otherwise we use a hashing algorithm on the
        first Constants.HASH_READ_BYTES of the file.

        We return the info and the discriminating data. For the smaller
        files, we prefix it with an 'R' (raw); for the larger, we prefix
        with an 'H' (Hashed) and the size as binary data.

        This further reduces the chances of discriminators or hashes
        colliding.
        """

        infh = safe_open(info.path)
        if infh:
            read_size = min(info.size, Constants.HASH_READ_BYTES)
            if read_size <= Constants.RAW_READ_BYTES:
                return info, b'R'+infh.read(read_size)
            else:
                hasher = hashlib.sha512()
                hasher.update(infh.read(read_size))
                return info, b'H'+struct.pack("Q", info.size)+hasher.digest()
        return None, None


    def _get_candidates(self):
        """
        Yields lists of FileInfos that have been size-matched and then
        hash (or raw-read) matched efficiently across threads.
        """

        total_files     = 0
        size_table      = defaultdict(list)  # {size: list(FileInfo)}
        files_raw       = 0
        files_hashed    = 0

        pool_map = self.pool.imap_unordered

        # Invoke the _get_files generate and farm the resulting path lists
        # to worker threads to stat and translate those that match our
        # criteria into FileInfos in size buckets.
        #
        self.logger.info("building size dict")
        for fi in pool_map(self._get_file_info, self._get_files(),
                           chunksize=Constants.STAT_CANDIDATE_CHUNKSIZE):
            if fi:
                total_files += 1
                size_table[fi.size].append(fi)

        # Eliminate unique sizes since they can't be duplicates of anything.
        matched_sizes = (l for l in size_table.values() if len(l) > 1)
        # since the above was a generator, we have to repeat the test
        num_candidates = sum(len(l) for l in size_table.values() if len(l) > 1)

        self.logger.debug("files:%d, sizes: %d, hashing candidates: %d" % (
                        total_files, len(size_table), num_candidates))

        # Sort the infos into buckets based on hashes, this will produce the
        # list of files that should be compared with each other.
        self.logger.info("hashing %d files" % num_candidates)
        buckets = defaultdict(list)
        for (info, key) in pool_map(self._hash_file,
                                    chain.from_iterable(matched_sizes),
                                    chunksize=Constants.HASH_FILE_CHUNKSIZE):
            if info:
                if key[0] == b'R':
                    files_raw += 1
                else:
                    files_hashed += 1
                buckets[key].append(info)

        self.logger.debug('raw files: %d, hashed: %d, hashes: %d' % ((
                        files_raw, files_hashed, len(buckets))))

        # Now yield list(FileInfo) based on hash buckets where the bucket
        # contains more than one entry (ie is not unique)
        yield from (list_fi for list_fi in buckets.values() if len(list_fi) > 1)


    def _compare_files(self, candidates):
        """
        Yields lists of matching files.

        :param candidates:  List of FileInfos of the files to be compared,
        :return:            list(FileInfo{2,}) of matched files or empty list,
        """

        file_size = candidates[0].size
        self.logger.debug("comparing {src} ({sz:n} bytes) vs {fls}".format(
            src=candidates[0].path, sz=file_size,
            fls=', '.join(i.path for i in candidates[1:])
        ))

        # Create 'Candidate' objects for each fileinfo, which allows us
        # to track all the files that are equal to each other as we read.
        # Imagine we have four files, which all start with 10k of 0s,
        # after which two of the files have 10k of 255s and the other two
        # have 10k of 1s: For the first 10k, all four files will have
        # each other as candidates. When the data diverges, only the files
        # who have matched so far will continue comparing data.
        candidates = (Candidate(fi) for fi in candidates)
        candidates = [c for c in candidates if c.fh]
        if len(candidates) < 2:
            return

        for idx in range(len(candidates)):
            candidates[idx].init(idx, candidates)

        # The 'matched' set will be used to avoid re-comparing data.
        # The 'lost' set will be used by each left index to track which
        # candidates just stopped matching with it.
        matched, lost, bytes_read = set(), set(), 0

        while bytes_read < file_size:

            # Read the next chunk of all active candidates.
            samples = {
                idx: candidates[idx].fh.read(Constants.READ_CHUNK_SIZE)
                for idx in range(len(candidates))
                if candidates[idx].candidates
            }
            # If no files were compared, nothing matches.
            if not samples:
                return None

            bytes_read += Constants.READ_CHUNK_SIZE

            # Now compare each candidate L with all the candidates in the
            # list after it, so long as neither has been matched this round.
            # So if file 0 matches 3 and 5, we will compare 1 with 2 and 4.
            matched.clear()
            for left_idx in range(len(samples) - 1):  # -1: we compare with idx + 1
                if left_idx not in samples or left_idx in matched:
                    continue
                lost.clear()
                for right_idx in range(left_idx + 1, len(samples)):
                    if right_idx not in samples or right_idx in matched:
                        continue
                    if right_idx not in candidates[left_idx].candidates:
                        continue
                    if samples[left_idx] == samples[right_idx]:
                        matched.add(left_idx)
                        matched.add(right_idx)
                        continue
                    # No match, these two are no-longer candidates
                    lost.add(right_idx)

                if lost:
                    candidates[left_idx].discount(lost, candidates)

        # Take each candidate that matched something and build their match
        # into a combination index in the matched set.
        matched.clear()
        for idx in range(len(candidates)):
            cand = candidates[idx]
            if cand.candidates:
                matched.add(tuple(sorted([idx] + list(cand.candidates))))

        for match_list in matched:
            yield (candidates[idx].fileinfo for idx in match_list)


    def matching_files(self):
        """
        Generator: Yields (size, list(filepath)) for lists of files that have
        been found to be exact duplicates.

        :return: tuple(size_in_bytes, list(filepaths))
        """

        raw_matches, hash_matches = 0, 0

        for size_list in self._get_candidates():
            size = size_list[0].size

            # Files that were small enough that we used the content instead
            # of the hash, so we can already tell they are an exact match.
            if size <= Constants.RAW_READ_BYTES:
                self.logger.debug('%d raw matches size %d' % (len(size_list),
                                                              size))
                yield size, list(i.path for i in size_list)

                raw_matches += len(size_list)
                continue

            # Larger files we're going to have to re-read and do a bytewise
            # comparison.
            hash_matches += len(size_list)

            matched, groups = set(), 0
            for match_list in self._compare_files(size_list):
                yield size, list(info.path for info in match_list)
                groups += 1

            logging.debug('size: %d, groups: %d, dupes: %d' % (size, groups,
                                                               len(matched)))

        logging.debug('%d raw matches, %d hashed matches' % (raw_matches,
                                                             hash_matches))


def parse_arguments(arglist):

    parser = argparse.ArgumentParser('finddupes')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increase output verbosity')
    parser.add_argument('--json', action='store_true',
                        help='Output in json format')
    parser.add_argument('--ge', type=int,
                        help='Only consider files >= this size.')
    parser.add_argument('--le', type=int,
                        help='Only consider files <= this size.')
    parser.add_argument('--threads', '-t', type=int,
                        help='Specify the number of threads.')
    parser.add_argument('--ignore-dirs', '-I', type=str, dest='ignore_dirs',
                        default=[], action='append',
                        help='Absolute directories to ignore.')
    parser.add_argument('paths', nargs='+', type=str, default=[],
                        help='Specify which path to search.')
    parser.add_argument('--output', '-O', type=str,
                        help='Output to this file (as utf-8)')

    return parser.parse_args(arglist)


if __name__ == "__main__":

    args = parse_arguments(sys.argv[1:])

    if not args.verbose:
        logLevel = logging.WARNING
    else:
        logLevel = logging.INFO if args.verbose == 1 else logging.DEBUG
    logging.basicConfig(level=logLevel, stream=sys.stderr)

    if args.output:
        encoding = "utf-8"
        outf = open(args.output, "w", encoding=encoding)
    else:
        outf = sys.stdout
        encoding = outf.encoding

    if args.json:
        import json

    paths = args.paths or ['.']
    cat = Catalog(folders=paths, min_size=args.ge, max_size=args.le,
                  ignore_folders=args.ignore_dirs, verbosity=args.verbose-1,
                  threads=args.threads, logger=logging)
    matches = list(cat.matching_files())

    if not matches:
        if args.verbose:
            logging.info("No duplicates found.")
        sys.exit(0)

    if args.json:
        print(json.dumps(matches), file=outf)
        sys.exit(0)

    maxlen = max(len("{:,}".format(m[0])) for m in matches)
    for size, files in matches:
        if args.verbose > 2:
            logging.debug("sz:%s fls:%s" % (size, files))
        # windows console :(
        if sys.platform == 'win32' or args.output:
            files = (fn.encode(encoding, errors='replace') for fn in files)
            files = (fn.decode(errors='replace') for fn in files)
        files = ','.join(files)
        print("{sz:{ml},} {fls}".format(ml=maxlen, sz=size, fls=files),
              file=outf)
