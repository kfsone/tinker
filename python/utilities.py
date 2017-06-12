# Copyright (C) 2017 Oliver "kfsone" Smith <oliver@kfs.org>
# Provided under The MIT License -- see LICENSE.

from __future__ import absolute_import
from __future__ import with_statement
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

"""
Miscellaneous utilities for my code.
"""

###############################################################################
#
def join_uri_paths(prefix, suffix):
    """
    Returns the uinion of two URI path strings without creating a double '/'
    between them.

    \param    prefix    The left side of the path,
    \param    suffix    The sub-path,
    \return             Combination of the two strings sans '//' in the middle.
    """

    prefix_end = -1 if prefix.endswith('/') else None
    suffix_start = 1 if suffix.startswith('/') else 0
    return prefix[:prefix_end] + '/' + suffix[suffix_start:]
