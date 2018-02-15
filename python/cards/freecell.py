""" Klondike module. """

###TODO:
### Track destination states so that we can track moves-to-state.
### Foundations only?

###TODO:
### Scoring:
###  -4 for every card in a stash,
###  -1 for every non-contiguous card,
###  +1 for every non-empty foundation,
###  +<value> for every card in the foundation,

from .common import Move, Store
from .cards import Card, Cards
from .faces import Faces
from .suites import Suites

from itertools import chain
from math import factorial
import types


# -----------------------------------------------------------------------------
#
class Stash(Store):
    """ An 'out-of-play' temporary store for cards. """

    def __init__(self, name):
        super(Stash, self).__init__([], 1, "Stash", name)

    def accepts(self, cards):
        if len(self.cards) + len(cards) > self.capacity:
            return False
        return True

    def available(self):
        return self.cards[0:]

    def extent(self):
        return 1

    def cardstr(self):
        return '('+self.cards[0].label+')' if self.cards else ""


# -----------------------------------------------------------------------------
#
class Foundation(Store):
    """ The destination for cards. """

    def __init__(self, suite, name):
        super(Foundation, self).__init__([], Faces.COUNT, "Suite", name)
        self.suite = suite
        self.label = Suites.label(suite)


    def accepts(self, cards):
        if len(cards) != 1:
            return False
        if cards[-1].suite == self.suite:
            previous_face = self.cards[-1].face if self.cards else Faces.LOW - 1
            if cards[0].face == previous_face + 1:
                return True
        return False


    def available(self):
        """ Cannot take cards from the foundation. """
        return None


    def cardstr(self):
        return (Cards.label(self.cards[-1].face) + self.label) if self.cards else ""


# -----------------------------------------------------------------------------
#
class Stack(Store):
    """ One of the rows that forms the deck. """

    def __init__(self, cards, name):
        super(Stack, self).__init__(cards, Faces.COUNT, "Deck", name)

    def accepts(self, cards):
        # Always validate that the cards will be contiguous.
        if self.extent(cards) != len(cards):
            return False
        if self.cards:
            prev, card = self.cards[-1], cards[0]
            if prev.color == card.color or prev.face != card.face + 1:
                return False
        return True

    def available(self):
        if not self.cards:
            return []
        num_cards = self.extent(self.cards)
        return self.cards[-num_cards:] if num_cards else []

    def extent(self, cards):
        """
        Determines the length (from the end) of a card sequence follow the
        Klondike rules (alternating color, contiguous face values).
        """

        if not cards:
            return 0
        card, num_cards = cards[-1], len(cards)
        for i in range(1, num_cards):
            prev, card = card, cards[-(i+1)]
            if card.color == prev.color or card.face != prev.face + 1:
                return i

        return num_cards


# -----------------------------------------------------------------------------
#
class Table(object):

    NUM_STACKS = 8
    """ How many stacks (vertical Stores) on the deck. """

    def __init__(self, deck, scoring):

        if not deck:
            raise ValueError("Must supply a deck for the table.")
        if not callable(scoring):
            raise ValueError("'scoring' must be callable.")

        # The deck is provided left-to-right, top-to-bottom, we need to convert
        # it into top-down, left-to-right. But we also need to start by padding
        # the deck to the right size, since some columns will be short.
        stacks = [[]]*Table.NUM_STACKS
        for stack_index in range(Table.NUM_STACKS):
            stack = []
            for card_index in range(stack_index, len(deck), Table.NUM_STACKS):
                stack.append(Cards.get_card(label=deck[card_index]))
                assert stack[-1].label == deck[card_index]
            stacks[stack_index] = Stack(stack, "Stack %d" % stack_index)

        self.stashes = (Stash("Stash 1"), Stash("Stash 2"), Stash("Stash 3"), Stash("Stash 4"))
        self.foundations = tuple(Foundation(suite, Suites.label(suite)) for suite in range(Suites.COUNT))
        self.deck = tuple(stacks)

        self.stores = tuple(chain(self.foundations, self.deck, self.stashes))
        self.moves = []

        self.scoring = scoring

    def score(self):
        return self.scoring(self)

    def apply_move(self, move):
        """
        Applies the specified move to the table state and tests if the
        move would win the table.

        :param move: A Move specifying the source, cards and destination.
        :return: True if this clears the table, else False.
        """

        move.source.cards[:] = move.source.cards[:-len(move.cards)]
        move.dest.cards += move.cards
        self.moves.append(move)
        if move.dest in self.foundations and move.source.empty():
            # When we empty something, check if we just cleared the deck,
            # by checking if all the foundations are now full.
            return all(f.full() for f in self.foundations)
        return False

    def undo_move(self):
        """ Reverses the last move of the table. """
        move = self.moves.pop()
        move.dest.cards[:] = move.dest.cards[:-len(move.cards)]
        move.source.cards += move.cards

    def draw(self):
        """ Ascii rendering of the table. """

        empty = ' - '
        stashes = ' '.join([empty if not stash.cards else stash.cards[0].label for stash in self.stashes])
        print("[%s]  Score: %d" % (stashes, self.score()))
        for i in self.foundations:
            foundation = '/'.join('%3s' % c.label for c in i.cards) + "|"
            print(i.name[0], foundation)
        tallest = max(len(s.cards) for s in self.deck)
        if not tallest:
            return
        for row in range(tallest):
            for col in range(self.NUM_STACKS):
                if row >= len(self.deck[col].cards):
                    card = empty
                else:
                    card = '%3s' % self.deck[col].cards[row].label
                print(card + ' ', end='')
            print()

    def cardstr(self):
        
        return "".join(sorted(s.cardstr() for s in self.stores))

    def next_moves(self):
        """
        Generator: Yields all possible Moves (source--cards->dest) from the maximum
        available for each source to the minimum.

        :yield: Move(source, cards, destination)
        """

        # Try moves in the preferred order, which is:
        #  stash->foundation,
        #  deck->foundation,
        #  stash->deck,
        #  deck->deck,
        #  deck->stash,

        # If the lowest foundation card is currently exposed, that will be our only move.
        lowest_foundation = min(f.cards[0].face if f.cards else 0 for f in self.foundations) + 1
        for source in (store for store in chain(self.deck, self.stashes) if store.cards):
            top_card = source.cards[-1]
            if top_card.face == lowest_foundation:
                foundation = self.foundations[top_card.suite]
                yield Move(source, [top_card], foundation)
                return

        # Try to transfer stash/deck cards to the foundation.
        for source in (store for store in chain(self.deck, self.stashes) if store.cards):
            top_card = source.cards[-1]
            dest = self.foundations[top_card.suite]
            dest_accepts = dest.cards[-1].face + 1 if dest.cards else Faces.LOW
            if dest_accepts == top_card.face:
                yield Move(source, [top_card], dest)

        # Try to move things out of the stashes.
        for source in (stash for stash in self.stashes if stash.cards):
            top_card = source.cards[-1]
            top_move = [top_card]
            foundation = self.foundations[top_card.suite]
            foundation_accepts = foundation.cards[-1].face + 1 if foundation.cards else Faces.LOW
            if foundation_accepts == top_card.face:
                yield Move(source, top_move, foundation)
            for dest in self.deck:
                yield Move(source, top_move, dest)

        # Try to move things out of the deck.
        free_spaces = max(sum(1 for s in chain(self.stashes, self.deck) if not s.cards),  1)
        for source in (store for store in self.deck if store.cards):
            # Is there an empty stash?
            empty_stashes = [s for s in self.stashes if not s.cards]
            if empty_stashes:
                yield Move(source, source.cards[-1:], empty_stashes[0])

            # Try moving between decks; only attempt one empty dest stack.
            for dest in self.deck:
                if dest is source:
                    continue
                available = source.available()
                max_cards = max(dest.capacity, free_spaces)
                if len(available) > max_cards:
                    available = available[-max_cards:]
                for offset in range(len(available)):
                    cards = available if offset == 0 else available[offset:]
                    yield Move(source, cards, dest)
