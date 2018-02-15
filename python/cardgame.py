from cards import freecell
from cards.cards import Cards
from contextlib import contextmanager
from cards import scoring

import argparse
import logging
import sys

# Winning a game is a matter of reaching a state where no cards are left in play,
# and the objective is to find the sequence of moves that transitions us from the
# initial state to the goal.


# -----------------------------------------------------------------------------
#
class TableState(object):
    """
    A TableState is the resulting table condition after applying a Move to a prior
    table state. The Goal state, no cards in play, will be the result of, e.g,
    moving a King from a stack onto a foundation.

    We can use this to detect loops (a->b, c->d, e->f, b->a, d->c, f->e results in
    reaching the original state), but also to detect achieving faster paths to a
    desirable state (d1[-1] -> d2, d1[-1] -> d3, d2[-1] -> d3 could be better achieved
    by trying d1[-2:] -> d3).
    """

    WINNER = "GOAL"
    """ Fake cardstr we'll use for the cleared table. """


    def __init__(self, score, move, cards_to_play=Cards.COUNT, parent=None):
        self.score = score
        self.move = move
        self.cards_to_play = cards_to_play
        self.parent = parent

    def find_depth(self):
        depth = 0
        cur = self.parent
        while cur:
            depth += 1
            cur = cur.parent
        return depth

    def moves(self):
        """
        Get the thus-far discovered move sequence to reach this state.

        :return: list(Move)
        """

        moves = []
        while self.move:
            moves += [self.move]
            self = self.parent
        return moves[::-1]


# -----------------------------------------------------------------------------
#
class Game(object):
    """
    Manage the tracking of attempts to complete a given deck.
    """

    def __init__(self, deck, scoring, max_moves=None, logger=logging):
        """
        
        :param deck:        The list of card labels representing the initial
                            deck state assumed left-to-right, top-to-bottom.
        :param scoring:     Callable(table) that assigns a score to a deck
                            configuration, with higher scores equating to a
                            presumed more-desirable table state. A won table
                            should have the highest possible score.
        :param max_moves:   Maximum number of moves to allow (default: number
                            of cards in deck multiplied by 4 + 1)
        :param logger:      Which logger to use.
        """

        if not max_moves:
            max_moves = len(deck) ** 4 + 1

        self.table = freecell.Table(deck, scoring)
        self.max_moves = max_moves
        self.logger = logger

        self.states = dict()
        self.default_state = TableState(self.table.score(), [])
        self.states[self.table.cardstr] = self.default_state

        self.winner = None
        self.winning_depth = max_moves + 1
        self.best_score = -9999999999

        self.logger.debug("Game with deck of %d cards: %s. Max moves: %d" % (
            len(deck), ",".join(deck), self.max_moves
        ))


    # -------------------------------------------------------------------------
    #
    @contextmanager
    def try_move(self, move):
        """ Try a move, yield, and undo the move. """
        yield self.table.apply_move(move)
        self.table.undo_move()
    
    
    # -------------------------------------------------------------------------
    #
    def solve(self):
        """ Attempts to find the least-moves way to win the current deck. """

        table = self.table
        max_moves = self.max_moves

        iter_no = 0

        # Accumulate states to explore moves from onto a list.
        states = [self.default_state]
        while states:

            iter_no += 1
            if iter_no % 10000 == 0:
                self._report_stats(states, iter_no)
               
            # Take the most desirable state 
            state = states.pop(0)
            moves = state.moves()
            if len(moves) + state.cards_to_play >= max_moves:
                # Discard if it can no-longer improve our best-effort.
                continue

            ###TODO: Try to minimize.
            # Put the table back into its state.
            for move in moves:
                table.apply_move(move)

            # We can eliminate a lot of useless cases, including simple loops,
            # by checking for the case where we move N cards A->B and then try
            # to move <= N cards from B to anywhere else.
            if table.moves:
                last_dest, last_count = table.moves[-1].dest, len(table.moves[-1].cards)
            else:
                last_dest, last_count = None, 0

            changes = 0
            table_depth = len(table.moves)
            for move in table.next_moves():
                # Make sure that applying another move wouldn't put us over
                # the current limit or victory depth.
                if len(table.moves) + state.cards_to_play >= max_moves:
                    break
                # Prevent bounces.
                num_cards = len(move.cards)
                if move.source == last_dest and num_cards >= last_count:
                    continue
                # Simple count check to avoid the function accepts call.
                if len(move.dest.cards) + num_cards > move.dest.capacity:
                    continue
                if not move.dest.accepts(move.cards):
                    continue

                # Go ahead and try this move, see if it wins.
                with self.try_move(move) as is_winner:
                    if is_winner:
                        # See if it's an improved win.
                        if self._update_winner(states, table, state, move):
                            changes += 1
                            # Anyone else must now achieve a clear table in
                            # one less move than we just did.
                            max_moves = len(table.moves) - 1
                    else:
                        # Evaluate how our new state performs and remember it.
                        if self._score_state(states, table, state, move, max_moves):
                            changes += 1

            ###TODO: Try to undo less moves?
            while table.moves:
                table.undo_move()

            # If we potentially changed the states list, resort it.
            if changes:
                states.sort(key=lambda st: (st.score, max_moves - st.find_depth() + st.cards_to_play), reverse=True)
                #states.sort(key=lambda st: st.score, reverse=True)


    def _update_winner(self, states, table, state, move):

        new_depth = len(table.moves)
        if self.winning_depth <= new_depth:
            self.logger.warn("Redundant win!")
            return False

        # Instead of a table state, we just use the word "WIN".
        winning_state = TableState(table.score(), move, 0, state)
        self.states[TableState.WINNER] = winning_state
        self.winner = winning_state
        self.winning_depth = new_depth

        self.logger.info("Win with %d moves from %d<-%d<-%d", new_depth,
            state.score, state.parent.score, state.parent.parent.score,
        )
        self.logger.debug("* %s", ", ".join(str(m) for m in winning_state.moves()))

        return True


    def _score_state(self, states, table, from_state, move, max_moves):
        new_depth = len(table.moves)
        cardstr = table.cardstr()
        table_state = self.states.get(cardstr)
        if table_state:
            old_depth = table_state.find_depth()
            # Unless this is an improvement (lower depth), ignore it.
            if new_depth >= old_depth:
                return False

        new_score = table.score()
        if new_score > self.best_score:
            self.logger.debug("depth=%3d best score=%d", new_depth, new_score)
            self.best_score = new_score

        # Count the number of cards in the foundation in this state.
        cards_to_play = Cards.COUNT - sum(len(f.cards) for f in table.foundations)

        if table_state:
            table_state.score = new_score
            table_state.move = move
            table_state.parent = from_state
            new_state = table_state
        else:
            new_state = TableState(new_score, move, cards_to_play, from_state)
            self.states[cardstr] = new_state

        if new_depth + cards_to_play + 1 >= max_moves:
            return bool(table_state)

        states.append(new_state)
        return True


    def _report_stats(self, states, iter_no):
        max_depth = max(s.find_depth() for s in states)
        self.logger.debug("iter: %d, md: %d, pending states: %d, seen states: %d",
                iter_no, max_depth, len(states), len(self.states))


def test_setup(filename=None, max_moves=200, scoring=scoring.score_counts, logger=logging):
    from cards import training

    scrn = training.train_from_default()
    deck = scrn.generate_deck(filename=filename)

    return Game(deck, max_moves=max_moves, scoring=scoring, logger=logger)


def parse_args(argv):

    parser = argparse.ArgumentParser("Solve Freecell deck")

    binary_file = argparse.FileType('rb')

    parser.add_argument("--verbose",    "-v",   dest="verbose",     action="count",         default=0,
            help="Increase logging verbosity.")
    parser.add_argument("--max-moves",  "-M",   dest="max_moves",   type=int,               default=200,
            help="Set the maximum number of moves to consider (default: 200).")
    parser.add_argument("--step",               dest="step",        action="store_true",    default=False,
            help="Walk the user thru the winning steps interactively on completion.")

    parser.add_argument("filename",             nargs='?',          type=binary_file,       default=None,
            help="Specify filename to read deck from. Default: Use the training deck (for demonstration).")

    return parser.parse_args(argv)


if __name__ == "__main__":

    args = parse_args(sys.argv[1:])

    if not args.verbose:
        log_level = logging.WARN
    elif args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("freecell")
    logger.setLevel(log_level)

    game = test_setup(
            filename=args.filename,
            max_moves=args.max_moves,
            scoring=scoring.score_values_model_1,
            logger=logger,
    )

    table = game.table
    table.draw()

    game.solve()
    if not game.winner:
        print("No winning sequence found.")
        sys.exit(1)

    for move_no, move in enumerate(game.winner.moves(), 1):

        cards = "/".join(c.label for c in move.cards)

        if not move.dest.cards:
            dest = "empty " + move.dest.typename
        else:
            dest = move.dest.cards[-1].label + " " + move.dest.typename

        if args.step:
            print("-" * 42)
            table.draw()
            print()
        print("#%3d: Move" % move_no, cards, "onto", dest)

        table.apply_move(move)

        if args.verbose >= 2:
            table.draw()
            print()

        if args.step and move_no < len(game.winning_depth):
            input("OK> ")
