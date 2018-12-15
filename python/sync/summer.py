#! /usr/bin/env python
#
# Takes a block number followed by a list of files, and returns the md5 checkum
# of the Nth block of each file.
#
# e.g. 0 /etc/motd /etc/motd.issue
# will yield the checksum of block 0 (the first 64k) of motd and motd.issue
#
# Output format is:
#
# <filename> <md5sum for the given block>

from __future__ import print_function

import hashlib
import mmap
import sys

BlockSize = 64 * 1024

block, files = int(sys.argv[1]), sys.argv[2:]
start_offset = BlockSize * block

for filename in files:
    with open(filename, "rb") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        length = min(mm.size() - start_offset, BlockSize)
        buf = buffer(mm, start_offset, length)
        del mm
        hashval = hashlib.md5(buf)
    print(filename, hashval.hexdigest())

