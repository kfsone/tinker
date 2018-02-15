""" Common classes/definitions to all card games. """

# -----------------------------------------------------------------------------
#
class Store(object):
    """ Any place that cards can be moved into or out of. """

    def __init__(self, cards, capacity, typename, name):
        self.cards = [None]*capacity
        self.cards[:] = cards
        self.capacity = capacity
        self.typename = typename
        self.name = name

    def accepts(self, cards):
        raise NotImplementedError()

    def available(self):
        raise NotImplementedError()

    def empty(self):
        return not bool(self.cards)

    def full(self):
        return bool(len(self.cards) == self.capacity)

    def cardstr(self):
        """ Flat-text representation of the card list. """
        return '['+"".join(c.label for c in self.cards)+']'


# -----------------------------------------------------------------------------
#
class Move(object):
    """ Simple container for describing movement of cards. """
    def __init__(self, source, cards, dest):
        self.source = source
        self.cards = tuple(cards)
        self.dest = dest

    def __str__(self):
        if len(self.cards) == 1:
            cards = self.cards[0].label
        else:
            cards = "(%s)" % ",".join(c.label for c in self.cards)
        return "%s->%s" % (cards, self.dest.typename)

    def __repr__(self):
        return "Move('%s', (%s), '%s')" % (
                self.source.name,
                ",".join(c.label for c in self.cards),
                self.dest.name,
        )
