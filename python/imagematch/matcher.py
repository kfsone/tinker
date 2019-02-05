#! /usr/bin/env python3

# Find images that are similar to each other

import imagehash
import os
from os.path import abspath as abspath, join as joinpath, normpath
from PIL import Image
from scipy.spatial.distance import hamming as hamming_distance


class Constants:
    
    DEFAULT_DHASH_THRESHOLD =   0.25
    DEFAULT_PHASH_THRESHOLD =   0.1

    DEFAULT_EXTENSIONS      =   ('.jpg', '.jpeg', '.gif', '.tga', '.bmp', '.png')


class ImageMatch(object):
    """ Tracks a match between two different images """

    def __init__(self, lhs_path, rhs_path, dist, alg):
        # Names of the two files
        self.files    = (lhs_path, rhs_path)
        # Hamming distance between the two (0=exact match, 1=no comparison)
        self.dist     = dist
        self.alg      = alg


    def update(self, dist, alg):
        self.dist = dist
        self.alg  = alg

    def __repr__(self):
        return "<%s(files=(%s, %s), %s=%f)>" % (
            self.__class__.__name__,
            self.files[0], self.files[1],
            self.alg, self.dist
        )


class ImageInfo(object):
    """
    Tracks details of an image: path, dhash, phash and matches.

    Initially only the dhash and matches are calculated. Once you have found
    possible close matches, you can then use the slower phash to finess the
    comparisons.

    See ImageInfo.Images() for all ImageInfo objects that were loaded.

    Call Reset() to clear the list.
    """

    IMAGES = {}
    """ Track images we've seen """


    # -------------------------------------------------------------------------
    # Class methods

    @classmethod
    def Images(kls):
        """ Returns a list of all the images that have been loaded. """
        return kls.IMAGES


    @classmethod
    def Matches(kls):
        """ Returns a generator expression of images that found a match. """
        return (inf for inf in kls.IMAGES.values() if inf.matches)


    @classmethod
    def Reset(kls):
        """ Clear all currently loaded ImageInfos. """
        kls.IMAGES = {}


    @classmethod
    def GetFiles(kls, path=".", recurse=False):
        """
        Yields field paths from 'path' that match known image extensions.

        :param  path:       Path to search (default %s)
        :param  recurse:    Set True to recursively descend sub-folders (default %s)
        """ % (".", False)

        extensions = tuple(set(Constants.DEFAULT_EXTENSIONS))

        for folder, dirs, files in os.walk(abspath(normpath(path))):
            if recurse:
                dirs[:] = [d for d in dirs if d not in ('.svn', '.hg', '.git')]
            else:
                dirs[:] = ()
    
            for f in (f for f in files if f.endswith(extensions)):
                yield joinpath(folder, f)


    @classmethod
    def PHashFilter(kls, threshold=Constants.DEFAULT_PHASH_THRESHOLD):
        matched = set()
        for lhs in kls.Matches():
            lhs_filepath = lhs.filepath
            fileset      = set((lhs_filepath,))
            matched.add(lhs_filepath)

            for match in list(lhs.matches):
                rhs_filepath = list(set(match.files) - fileset)[0]
                if rhs_filepath in matched:
                    continue
                matched.add(rhs_filepath)
                rhs = kls.IMAGES[rhs_filepath]
                pdist = hamming_distance(lhs.phash, rhs.phash)
                if pdist > threshold:
                    lhs.matches.remove(match)
                    rhs.matches.remove(match)
                    print("Removed: %s<->%s" % (lhs_filepath, rhs_filepath))
                else:
                    match.update(pdist, "phash")


    # -------------------------------------------------------------------------
    # Instance methods

    def __init__(self, filepath):
        self.filepath = filepath
        self.dhash    = None
        self._phash   = None
        self.matches  = []


    def register(self, threshold=Constants.DEFAULT_DHASH_THRESHOLD):
        """
        Populates the dhash and matches values and registers the ImageInfo to
        the class's currently tracked image list (see ImageInfo.Images).

        :param threshold: 0.<=threshold<=1.0 only hamming distances <= threshold
                          will be considered a match (default %f).
        """ % Constants.DEFAULT_DHASH_THRESHOLD

        # Calculate the dHash of my own image.
        if self.dhash is None:
            with Image.open(self.filepath) as image:
                dhash_str = str(imagehash.dhash(image))
                self.dhash = dhash_str

        # Now compare with the other images already registered
        for rhs_filepath, rhs_info in ImageInfo.IMAGES.items():
            dist = hamming_distance(dhash_str, rhs_info.dhash)
            if dist <= threshold:
                match = ImageMatch(self.filepath, rhs_filepath, dist, "dhash")
                self.matches.append(match)
                rhs_info.matches.append(match)

        # Now append ourselves to the currently-tracked images
        self.IMAGES[self.filepath] = self


    @property
    def phash(self):    
        if self._phash is None:
            with Image.open(self.filepath) as image:
                self._phash = str(imagehash.dhash(image))
        return self._phash


    def __repr__(self):
        return "<%s(filepath=%s, dhash=%s, phash=%s, matches=%s)>" % (
            self.__class__.__name__,
            self.filepath, self.dhash, self.phash, self.matches
        )
