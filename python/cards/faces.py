""" Describes the faces available within the suites (Ace, 2, King, etc). """


class Faces:
    """ Enumerate and index faces. """

    Ace = 1
    Two = 2
    Three = 3
    Four = 4
    Five = 5
    Six = 6
    Seven = 7
    Eight = 8
    Nine = 9
    Ten = 10
    Jack = 11
    Queen = 12
    King = 13

    LOW = Ace
    """ Which face is the lowest value. """
    HIGH = King
    """ Which face is the highest value. """
    COUNT = HIGH - LOW + 1
    """ How many faces are there? In this case it's straight forward. """

    INDEX = ('A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K')
    """ Ordered list of faces. """

    @staticmethod
    def index(label):
        return Faces.INDEX.index(label) + 1

    @staticmethod
    def label(face):
        """ Return the representative label for this face. """
        return Faces.INDEX[face - 1]    # Card numbers are 1-based.
