""" Scoring algorithms for games. """

from .cards import Cards
from .faces import Faces

from itertools import chain
from math import factorial


def score_deck_counts(table, per=1):
    """ -1 point for every card not in the foundation. """
    return -per * sum(len(s.cards) for s in table.deck if s.cards)

def score_stash_counts(table, per=1):
    """ Deduct points for cards in the stash. """
    return -per * sum(len(stash.cards) for stash in table.stashes if stash.cards)

def score_foundation_counts(table, per=1):
    """ Add points for every card in the foundation. """
    return per * sum(len(f.cards) for f in table.foundations if f.cards)

def score_deck_values(table):
    """ Deduct face values for cards on the deck and the stash. """
    return -sum(sum(1 + card.face for card in stack.cards)
                    for stack in table.deck if stack.cards)

def score_foundation_values(table):
    """ Add points for the value of every card in the foundations. """
    return sum(sum(Faces.LOW + c.face for c in f.cards)
                    for f in table.foundations if f.cards)

def score_foundation_unlocks(table, per=1):
    """ Add points for every unlocked (non-empty) foundation. """
    return sum(per for found in table.foundations if found.cards)

def score_stash_values(table):
    """ Deduct points for stash population. """
    return -sum(1 + stash.cards[-1].face + 1 for stash in table.stashes)    

def score_foundation_balance(table):
    """
    Finds the lowest card that has been unlocked in all foundations and
    returns a factorial score for it, or 0.
    """
    # What's the lowest card on any of the foundations?    
    lowest_unlocked = min(len(f.cards) for f in table.foundations)
    # For klondike, this conveniently means that a len of 0 means empty and a
    # len of 1 means it contains the ace, etc.
    return sum(range(1, lowest_unlocked + 1)) if lowest_unlocked else 0

def score_exposed_lows(table):
    """
    Deduct points for every stash/stack that has cards but is not topped by
    a card that can be moved to the foundation.
    """
    score = 0
    for cards in (src.cards for src in chain(table.stashes, table.deck) if src.cards):
        top_card = cards[-1]
        if not table.foundations[top_card.suite].accepts((top_card,)):
            score -= 4 * Faces.HIGH
    return score

### Complete models ###

def score_counts(table):
    """
    +1 per foundation card,
    -1 per deck card,
    -1 per stash card,
    """
    score = score_deck_counts(table) + score_stash_counts(table)
    score += score_foundation_counts(table)
    return score

def score_values(table):
    """
    like score_trivial but also counts values of deck and foundation cards.
    """
    score = score_deck_values(table) + score_stash_counts(table)
    return score + score_foundation_values(table)

def score_count_model_1(table):
    """
    Heavy penalty for stash cards (KING),
    -1 point for every card on the deck,
    +3 points for every unlocked foundation,
    +sum of faces in the foundations,
    """

    score = score_stash_counts(table, per=Faces.HIGH)
    score += score_deck_counts(table)
    score += score_foundation_unlocks(table, per=Faces.HIGH)
    score += score_foundation_values(table)

    return score

def score_values_model_1(table):
    """
    Heavy penalty for stash cards (KING),
    -1 point for every card on the deck,
    +3 points for every unlocked foundation,
    +sum of faces in the foundations,
    """

    # Extreme prejudice against
    score = score_stash_counts(table, per=Faces.HIGH+1)
    score += score_deck_values(table)
    score += score_foundation_unlocks(table, per=3)
    score += score_foundation_values(table)

    return score

def score_complex(table):
    score = score_deck_values(table) - score_stash_counts(table, per=Faces.HIGH)
    score += score_foundation_unlocks(table, per=Faces.HIGH)
    score += score_foundation_values(table)
    score += score_foundation_balance(table)
    #score += score_exposed_lows(table)
    return score

