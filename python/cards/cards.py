""" Provides the Card and Card classes. """

from itertools import product as iter_product
from .suites import Suites
from .faces  import Faces


class Cards:
    """ Enumerate all available cards. """

    INDEX = tuple(f+s for f, s in iter_product(Faces.INDEX, Suites.INDEX))
    """ Produce all combinations of "{face}{suite}" """

    COUNT = len(INDEX)
    """ Provides the pack size. """

    images = None
    """ If images have been provided, store here. """

    @staticmethod
    def index(card):
        """ Return the index of given card representation """
        return Cards.INDEX.index(card.upper())

    @staticmethod
    def label(index):
        """ Map a numeric value to a card label. """

        return Cards.INDEX[index]


class Card(object):
    """ Describe an individual card. """

    def __init__(self, suite=None, face=None, label=None):
        if suite and face:
            self.suite = suite
            self.face = face
        elif label:
            self.face, self.suite = Faces.index(label[:-1]), Suites.index(label[-1:])
        else:
            raise ValueError("Invalid arguments for Card()")
        self.label = Faces.label(self.face) + Suites.label(self.suite)
        self.index = Cards.INDEX.index(self.label)
        self.color = Suites.color(self.suite)
