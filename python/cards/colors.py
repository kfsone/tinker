""" Available colors. """

class Colors:
    """ Enumerate colors. """

    Red = 2 ** 0
    Black = 2 ** 1

    INDEX = ('Red', 'Black')
    """ Names for each color. """

    COUNT = 2
    """ Total number of colors. """

    @staticmethod
    def label(color):
        """ Return the representative label for a color. """

        return Colors.INDEX[color]
