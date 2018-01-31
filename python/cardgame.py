if __name__ == "__main__":
    from cards import training

    scrn = training.train_from_default()

    deck = scrn.generate_deck()

    from cards import klondike

    table = klondike.Table(deck)
    for play in table.score_plays():
        print(play)
