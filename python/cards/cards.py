""" Provides the Card and Card classes. """

from itertools import product as iter_product
from .suites import Suites
from .faces  import Faces


class Card(object):
    """ Describe an individual card. """

    def __init__(self, suite=None, face=None, label=None):
        self.suite, self.face, self.label = suite, face, label
        self.index = Cards.INDEX.index(label)
        self.color = Suites.color(suite)

    def __str__(self):
        return self.label

    def __repr__(self):
        return "Card(suite=%d, face=%d, label='%s')" % (
                self.suite, self.face, self.label
        )

class Cards(object):
    """ Enumerate all available cards. """

    INDEX = tuple(f+s for f, s in iter_product(Faces.INDEX, Suites.INDEX))
    """ Produce all combinations of "{face}{suite}" """

    COUNT = len(INDEX)
    """ Provides the pack size. """

    images = None
    """ If images have been provided, store here. """

    __cards = dict()
    """ Registry of known cards. """

    @staticmethod
    def index(card):
        """ Return the index of given card representation """
        return Cards.INDEX.index(card.upper())

    @staticmethod
    def label(index):
        """ Map a numeric value to a card label. """
        return Cards.INDEX[index]

    @staticmethod
    def get_card(suite=None, face=None, label=None):
        if label and suite is None and face is None:
            face, suite = Faces.index(label[:-1]), Suites.index(label[-1:])
        elif label:
            raise ValueError("Invalid arguments for get_card()")
        else:
            label = Faces.label(face) + Suites.label(suite)
        card = Cards.__cards.get(label)
        if not card:
            card = Cards.__cards[label] = Card(suite, face, label)
        return card

