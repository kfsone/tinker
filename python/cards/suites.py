""" Describe the available suites. """

from .colors import Colors


class Suites:
    """ Enumerate and index suites. """

    Hearts = Colors.Red + 0
    Diamonds = Colors.Red + 1
    Clubs = Colors.Black + 0
    Spades = Colors.Black + 1

    @staticmethod
    def color(suite):
        """ Returns the color for a given suite. """

        return Colors.Black if bool(suite & Colors.Black) else Colors.Red

    COUNT = 4
    """ Total number of suites. """

    INDEX = ('H', 'D', 'C', 'S')
    """ Label representation for each suite. """

    @staticmethod
    def index(label):
        return Suites.INDEX.index(label)

    @staticmethod
    def label(suite):
        """ Return the representative label for this suite. """

        # Suite numbers are 0-based.
        return Suites.INDEX[suite]
