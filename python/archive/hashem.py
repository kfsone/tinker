#! /usr/bin/python3

import argparse
import hashlib
import mmap
import os
import posixpath
import stat
import sys

from collections import namedtuple


exclusions = ('lost+found', 'restore', 'backup', 'Newsfeed', '.pki', 'Jenkins')

joinpath = posixpath.join


FileDesc = namedtuple('FileDesc', ['full_path', 'item_type', 'size', 'mtime', 'checksum'])

def get_file_desc(full_path, want_checksum):
    try:
        stinf = os.stat(full_path)
    except:
        return None
    if stat.S_ISREG(stinf.st_mode):
        item_type, item_size = 'F', stinf.st_size
    elif stat.S_ISDIR(stinf.st_mode):
        item_type, item_size = 'D', 0
    else:
        return None

    checksum = 0
    if item_type == 'F' and item_size > 0 and want_checksum(full_path):
        with open(full_path, 'rb') as fl:
            mm = mmap.mmap(fl.fileno(), 0, access=mmap.ACCESS_READ)
            checksum = hashlib.md5(mm).hexdigest().lower()
            mm.close()

    return FileDesc(full_path, item_type, item_size, stinf.st_mtime, checksum)


def get_file_stats(base_dir, exclusions, get_checksums=None):

    if get_checksums is None:
        want_checksum = lambda filename: False
    elif not get_checksums:
        want_checksum = lambda filename: True
    else:
        want_checksum = lambda filename: filename in get_checksums

    for base, dirs, files in os.walk(base_dir):

        if base == base_dir:
            # Skip top-level cruft
            dirs[:] = [d for d in dirs if d not in exclusions]

        for filename in files:

            fd = get_file_desc(posixpath.join(base, filename), want_checksum)
            if fd:
                yield fd


def ls_cmd(args):
    if args.checksum:
        get_checksums = []
    else:
        get_checksums = args.filepath or None

    for filedesc in get_file_stats(args.base_dir, exclusions, get_checksums):
        print("{},{},{},{},{}".format(filedesc.item_type, filedesc.size, filedesc.mtime, filedesc.checksum, filedesc.full_path))


class CompareError(Exception):
    def __init__(self, action, reason):
        super().__init__("Compare failed")
        self.action = action
        self.reason = reason
    

def cmp_cmd(args):
    do_checksum, dont_checksum = lambda fn: True, lambda fn: False
    with open(args.csv, "r") as fl:
        for line in (l.strip() for l in fl):
            if line:
                remote_fd     = FileDesc(line.split(',', 4))
                local_path    = os.path.normpath(os.path.join(args.base_dir, remote_fd.full_path))
                want_checksum = do_checksum if local_fd.checksum else dont_checksum
                local_fd      = get_file_desc(local_path, want_checksum)

                try:
                    if not local_fd:
                        raise CompareError("download", "missing")
                    if local_fd.item_type != remote_fd.item_type:
                        if remote_fd.item_type == 'D':
                            raise CompareError("mkdir", "changed")
                        elif remote_fd.item_type == 'F':
                            raise CompareError("download", "changed")
                    if remote_fd.size != local_fd.size:
                        raise CompareError("download", "size")
                    if remote_fd.checksum != local_fd.checksum:
                        raise CompareError("download", "checksum")
                    if remote_fd.mtime != local_fd.mtime:
                        os.utime(local_fd, (remote_fd.mtime, remote_fd.mtime))
                        raise CompareError("#touched", "mtime")
                except CompareError as e:
                    print("%s,%s,%s,%s" % (e.action, e.reason, remote_fd.mtime, remote_fd.full_path))    




if __name__ == "__main__":
    argp = argparse.ArgumentParser("hasher")
    argp.add_argument("--base-dir", "-C", dest="base_dir", default="/svn", help="Base folder")

    subp = argp.add_subparsers()

    lscmd = subp.add_parser("ls")
    lscmd.add_argument("--checksum", action="store_true", help="Force checksumming")
    lscmd.add_argument("filepath", action="append", default=[], nargs='*', help="File paths to check")
    lscmd.set_defaults(func=ls_cmd)

    cmpcmd = subp.add_parser("cmp")
    lscmd.add_argument("csv", type=str, help="CSV file to check against")

    args = argp.parse_args(sys.argv[1:])

    if not hasattr(args, 'func'):
        raise RuntimeError("No sub-command specified. See --help for assistance.")

    args.func(args)
