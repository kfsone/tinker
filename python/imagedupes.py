#! /usr/bin/env python3

import argparse
from imagematch.matcher import ImageInfo
import os
import sys


def parse_arguments(arglist):
    parser = argparse.ArgumentParser(arglist[0])

    parser.add_argument('--dhash', type=int, default=75,
                        help="Threshold for 'dhash' matching (percentage: 1-100)")
    parser.add_argument('--phash', type=int, default=90,
                        help="Threshold for 'phash' matching (percentage: 1-100)")

    parser.add_argument("paths", nargs='+',
                        help="List of folders to consider")

    args = parser.parse_args(arglist[1:])

    if args.dhash <= 0 or args.dhash > 100:
        raise ValueError("--dhash must be between 1-100")
    args.dhash = 1/(100-args.dhash)

    if args.phash <= 0 or args.phash > 100:
        raise ValueError("--phash must be between 1-100")
    args.phash = 1/(100-args.phash)

    paths = set()
    for path in args.paths:
        if not os.path.exists(path):
            raise ValueError("Non-existent path: %s" % path)
        absnorm = os.path.abspath(os.path.normpath(path)).rstrip(os.sep)
        if path.endswith(os.sep):
            absnorm += os.sep
        paths.add(absnorm)
    args.paths = paths

    return args

def main(arglist):

    args = parse_arguments(arglist)

    for path in args.paths:
        for filepath in ImageInfo.GetFiles(path, not path.endswith(os.sep)):
            ImageInfo(filepath).register(threshold=args.dhash)

    print("-- Analyzed images: %d" % len(ImageInfo.Images()))
    matches = list(ImageInfo.Matches())
    print("-- DHash matches  : %d" % len(matches))
    if not matches:
        return 0

    ImageInfo.PHashFilter(threshold=args.phash)
    matches = list(ImageInfo.Matches())
    print("-- PHash matches  : %d" % len(matches))
    if not matches:
        return 0

    matched = set()
    for info in matches:
        if info.filepath in matched:
            continue
        matched.add(info.filepath)
        print("%s:" % info.filepath)
        for match in info.matches:
            rhs = match.files[0] if match.files[1] == info.filepath else match.files[1]
            matched.add(rhs)
            dist = 100 - (int(1.0 / match.dist) if match.dist > 0.0 else 0)
            print("  %3d%%  %s" % (dist, rhs))
    

if __name__ == "__main__":
    main(sys.argv)
