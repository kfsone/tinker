""" Klondike module. """

from .cards import Card
from .faces import Faces
from .images import *
from itertools import chain


# -----------------------------------------------------------------------------
class Store(object):
    """ Any place that cards can be moved into or out of. """

    def __init__(self, cards, capacity, name):
        self.cards = [None]*capacity
        self.cards[:] = cards
        self.capacity = capacity
        self.name = name

    def accepts(self, cards):
        raise NotImplementedError()

    def available(self):
        return

    def withdraw(self, cards):
        raise NotImplementedError()

    def empty(self):
        return not bool(self.cards)


# -----------------------------------------------------------------------------
class Stash(Store):
    """ An 'out-of-play' temporary store for cards. """

    def __init__(self, name):
        super(Stash, self).__init__([], 1, name)

    def accepts(self, cards):
        assert cards
        if len(self.cards) + len(cards) > self.capacity:
            return False
        return True

    def available(self):
        if self.cards:
            return self.cards[0]  # Only one card is available
        return None

    def extent(self):
        return 1

    def withdraw(self, cards):
        assert cards
        if cards != self.cards:
            return False
        self.cards[:] = []
        return True


# -----------------------------------------------------------------------------
class Foundation(Store):
    """ The destination for cards. """

    def __init__(self, suite, name):
        super(Foundation, self).__init__([], Faces.COUNT, name)
        self.suite = suite

    def accepts(self, cards):
        if len(cards) != 1:
            return False
        previous_face = self.cards[-1].face if self.cards else Faces.LOW - 1
        return cards[0].face == previous_face + 1

    def available(self):
        """ Cannot take cards from the foundation. """
        return None

    def withdraw(self, cards):
        """ Cannot withdraw from the Foundation in Klondike. """
        return False


# -----------------------------------------------------------------------------
class Stack(Store):
    """ One of the rows that forms the deck. """

    def __init__(self, cards, name):
        super(Stack, self).__init__(cards, Faces.COUNT, name)

    def accepts(self, cards):
        assert cards
        # Always validate that the cards will be contiguous.
        if self.extent([self.cards[-1]]+cards) != len(cards) + 1:
            return False
        return True

    def available(self):
        num_cards = self.extent(self.cards)
        if num_cards == 0:
            return []
        return self.cards[-num_cards:]

    def extent(self, cards):
        """
        Determines the length (from the end) of a card sequence follow the
        Klondike rules (alternating color, contiguous face values).
        """

        if not cards: return 0
        card = cards[-1]
        for i in range(1, len(cards)):
            prev, card = card, cards[-(i+1)]
            if card.face != prev.face + 1 or card.color == prev.color:
                return i

        return len(cards)

    def withdraw(self, cards):
        # Can only withdraw stack-style.
        assert cards
        if self.extent(cards) != len(cards):
            return False
        removed, self.cards[:] = self.cards[-len(cards):], self.cards[:-len(cards)]
        assert removed == cards


# -----------------------------------------------------------------------------
class Table(object):

    NUM_STACKS = 8

    def __init__(self, deck):

        if not deck:
            raise ValueError("Must supply a deck for the table.")

        # The deck is provided left-to-right, top-to-bottom, we need to convert
        # it into top-down, left-to-right. But we also need to start by padding
        # the deck to the right size, since some columns will be short.
        stacks = [[]]*Table.NUM_STACKS
        for stack_index in range(Table.NUM_STACKS):
            stack = []
            for card_index in range(stack_index, len(deck), Table.NUM_STACKS):
                stack.append(Card(label=deck[card_index]))
                assert stack[-1].label == deck[card_index]
            stacks[stack_index] = Stack(stack, "Stack %d" % stack_index)

        self.stashes = (Stash("Stash 1"), Stash("Stash 2"), Stash("Stash 3"), Stash("Stash 4"))
        self.hearts = Foundation(Suites.Hearts, "Hearts")
        self.diamonds = Foundation(Suites.Diamonds, "Diamonds")
        self.spades = Foundation(Suites.Spades, "Spades")
        self.clubs = Foundation(Suites.Clubs, "Clubs")
        self.foundations = (self.hearts, self.diamonds, self.spades, self.clubs)
        self.deck = []
        self.deck = tuple(stacks)

    def scan_draws(self):

        # options for moving out of the stash:
        for src in chain(self.stashes, self.deck):
            avail = src.available()
            if avail:
                yield src, avail

    def scan_targets(self, source, cards):

        destinations = [self.foundations, self.deck]
        if not source in self.stashes:
            destinations.append(self.stashes)
        for dest in chain(*destinations):
            if dest is source:
                continue
            if dest.accepts(cards):
                labels = [c.label for c in cards]
                print("yielding %d cards (%s) from %s -> %s" % (len(labels), labels, source, dest))
                yield dest, cards

    def scan_plays(self):

        for src, cards in self.scan_draws():
            for offset in range(0, len(cards)):
                for dest, subset in self.scan_targets(src, cards[offset:]):
                    yield src, subset, dest

    def score_plays(self, lowest_card=Faces.Ace):

        # If the lowest_card is the ACE, then any aces that are exposed should
        # be moved to the foundations regardless of what other plays might be
        # available. Once all the aces have been moved, we should likewise
        # favor any 2s, then 3s, etc.
        #
        for src in (stack for stack in self.deck if not stack.empty()):
            top_card = src.cards[-1]
            if top_card.face == lowest_card:
                print("Found an exposed ace in %s: %s" % (src.name, top_card.label))
                yield 100, src, [top_card], self.foundations[top_card.suite]
                # No point in considering any other moves.
                return

        for src, cards, dest in self.scan_plays():
            # Are we turning in a card?
            if dest in self.foundations:
                # The lower the card, the better the score. This way we should
                # favor trying to move cards to the foundations first.
                score = Faces.HIGH - cards[0].face + 1
                yield score, src, cards, dest
            elif dest in self.stashes:
                score = -(Faces.HIGH - cards[0].face + 1)
                yield score, src, cards, dest
            else:
                ###TODO: Analyze and determine if there's a preferential order.
                yield 0, src, cards, dest
