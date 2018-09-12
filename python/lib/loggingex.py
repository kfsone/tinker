# -*- coding: iso-8859-15 -*-
#
# This module provides formatters and other logging support abut it also
# introduces two additional log levels to the logging module.
#
# The thinking is that, generally, Unix utilities should have minimal, if any,
# output. Silence = success.
#
# logging.NOTE:
# If the user wants some basic idea of what the application is doing, they add
# a '-v' option to the command line, and will see things like which major
# operations the code executes.
#
# logging.INFO:
# '-v -v' begins to introduce more detail of sub-operations that an end-user
# might need to analyze issues with the inputs they are providing.
#
# logging.DEBUG
# '-v -v -v' introduces diagnostic information that a developer but also
# a user with a deep issue to investigate might need.
#
# logging.SPAM
# '-v -v -v -v' adds relatively spammy debugging information that a developer
# might need for an in-depth analysis


import collections
import logging
import os
import sys


# -----------------------------------------------------------------------------
# Monkey-patch our own logging level information into the logging module.

logging.NOTE = logging.INFO  + 5
logging.SPAM = logging.DEBUG - 5

logging.addLevelName(logging.NOTE, "NOTE")
logging.addLevelName(logging.SPAM, "SPAM")

logging.note = lambda logger, *args, **kwargs: logger.log(logging.NOTE, *args, **kwargs)
logging.spam = lambda logger, *args, **kwargs: logger.log(logging.SPAM, *args, **kwargs)

logging.Logger.note = lambda logger, *args, **kwargs: logger.log(logging.NOTE, *args, **kwargs)
logging.Logger.spam = lambda logger, *args, **kwargs: logging.log(logging.SPAM, *args, **kwargs)

logging.root.note = lambda logger, *args, **kwargs: logging.log(logging.NOTE, *args, **kwargs)
logging.root.spam = lambda logger, *args, **kwargs: logging.log(logging.SPAM, *args, **kwargs)

""" List of logging levels ordered least important to most. """
logging.levels = (
        logging.NOTSET,
        logging.SPAM,
        logging.DEBUG,
        logging.INFO,
        logging.NOTE,
        logging.WARN,
        logging.ERROR,
        logging.FATAL,
)


def get_relative_level(level, offset):
    """
    Determine which log level is `offset` positions above/below the
    supplied log level, within the priority list. Thus NOTE +2 is ERROR.

    :param level:       The logging.XXX level base, e.g. logging.INFO,
    :param offset:      The relative offset within the logging.levels list,
    :return:            logging level at the given offset, bounds constrained.
    """

    # Find the level's priority index
    idx = logging.levels.index(level)

    # Adjust the index by offset, and then constrain it.
    adjusted = idx + offset
    adjusted = max(adjusted, 0)                         # >= 0
    adjusted = min(adjusted, len(logging.levels) - 1)   # <= highest levels index

    return logging.levels[adjusted]


class LoggingLimitError(Exception):
    """ Distinct exception thrown by ByLevelHandler """
    pass


class ByLevelHandler(logging.Handler):
    """
    Counts, and optionally limits, the number of messages reported by level.

    If 'messages' is a dictionary, it is assumed to be a mapping of
    log-level to list-like and will be used to store messages at those
    levels.

    Example:

            max_counts = {
                logging.WARNING: 10,        # max 10 warnings,
                logging.ERROR:    3,        # stop on 3rd warning,
            }
            messages   = {
                logging.WARNING: []         # Record WARNING messages
            }

            handler = ByLevelHandler(max_counts=max_counts, messages=messages)

        :param max_counts: Optional dictionary of {level: max messages}
        :param messages:   Optional dictionary of {level: append()able}
    """

    def __init__(self, max_counts=None, messages=None, *args, **kwargs):
        super(ByLevelHandler, self).__init__(*args, **kwargs)

        # Fast mapping of log-level to count of messages seen
        self.counts = collections.Counter()

        # Remember the user-specified ceiling for level counts.
        self.max_counts = max_counts or {}

        # User provided mutables to track messages.
        self.messages = messages or {}

        # Prevent infinite looping if we throw a warning.
        self.faulted = False


    def emit(self, record):
        self.counts[record.levelno] += 1

        # Prevent an exception handler logging a warning and recursing.
        if self.faulted:
            return

        # Are they expecting us to capture messages for this level?
        messages = self.messages.get(record.levelno, None)
        if messages is not None:
            messages.append(record.message)

        # Nothing else to do unless this is a level we're tracking.
        max_count = self.max_counts.get(record.levelno, 0)
        if max_count <= 0:
            return

        # Let it pass until we reach the limit.
        if self.counts[record.levelno] < max_count:
            return

        self.faulted = True

        msg = "Too many %s(s): aborting."
        raise LoggingLimitError(msg % logging.getLevelName(record.levelno))


    def report(self):
        """
        Returns a description of the logging activity so far.

        e.g.
            print(handler.report())

        :return: A string describing logging activity or None.
        """

        activity = ""

        for level_no in sorted(self.counts.keys(), reverse=True):
            level = logging.getLevelName(level_no)
            count = self.counts[level_no]
            activity += "  {0:8s} {1:5n}\n".format(level, count)

        return activity or None


class SubstitutionFormatter(object):
    """
    Formatter that replaces strings in log messages before presentation.

    For example, if you want to shorten the logging of long path names,
    e.g. /home/albert.einstein/relatively_long_path/readme.txt might
    become '$PROJECT/readme.txt'.

    Example:

        SubstitutionFormatter(text='/home/einstein', replacement='$HOME')

    :param text:        The path to substitute
    :param replacement: Variable name to sub with
    :param parent:      The predecessor formatter
    """


    def __init__(self, text, replacement, parent=None):
        self.needle = text
        self.subs   = replacement
        self.parent = parent


    def format(self, record):
        if self.parent:
            msg = self.parent(record)
        msg = msg.replace(self.needle, self.subs)


class LevelPrefixFormatter(logging.Formatter):
    """
    Prefixes each message with a string denoting its level. Default
    is the first character of the level, e.g. W] for warning.

    You can provide your own mapping or use on the supplied defaults:
        LevelPrefixFormatter.CharacterPrefixes, (default)
        LevelPrefixFormatter.SymbolicPrefixes,

    :param prefixes:    Map of { level: prefix text },
    :param parent:      Parent formatter
    """

    CharacterPrefixes = {
        logging.SPAM:       'S] ',
        logging.DEBUG:      'D] ',
        logging.NOTE:       'N] ',
        logging.INFO:       'I] ',
        logging.WARNING:    'W] ',
        logging.ERROR:      'E] ',
        logging.FATAL:      'F] ',
        'default':          '?] ',
    }
    SymbolicPrefixes = {
        logging.SPAM:       '### ',
        logging.DEBUG:      '#   ',
        logging.NOTE:       '--- ',
        logging.INFO:       '(I) ',
        logging.WARNING:    '(!) ',
        logging.ERROR:      '*** ',
        logging.FATAL:      '!!! ',
        'default':          '??? ',
    }

    DefaultPrefixes = CharacterPrefixes

    def __init__(self, prefixes=None, parent=None):
        if prefixes is None:
            prefixes = LevelPrefixFormatter.DefaultPrefixes
        if parent is None:
            raise ValueError("Cannot be top-level formatter")
        self.parent = parent
        self.default = prefixes['default']

    def format(self, record):
        prefix = self.prefixes.get(record.levelno, self.default)
        return prefix + self.parent(record)

