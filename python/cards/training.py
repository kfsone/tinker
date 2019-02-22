""" Generates the map of card images from a screenshot. """

from .images import Screenshot
import os

# An image containing a screenshot of a deck
TRAINING_IMAGE = os.path.join('cards', 'training.png')
# And the deck in the image (l->r, t->b)
TRAINING_DECK = (
    'JC', '7C', '5S', '5C', '6C', '5H', '9D', '3D',
    'KS', '6S', 'QS', '8C', '3S', 'KD', '8H', '5D',
    'QC', 'QD', '7S', 'JS', 'KH', '2D', 'QH', 'AS',
    '8D', 'AD', '4S', '8S', '10S', '9H', '3H', 'AH',
    'AC', 'KC', '4C', 'JD', '3C', '2C', '9C', '10H',
    '2H', '6H', 'JH', '7H', '2S', '10C', '4H', '7D',
    '10D', '4D', '6D', '9S'
)


# Coordinates for the screenshot:
class Info:
    TOP_LEFT = (504, 348)
    SPACING = (202, 56)
    COLUMNS = 8
    ROWS = 7
    SPACE = (COLUMNS * SPACING[0], ROWS * SPACING[1])
    BOTTOM_RIGHT = (TOP_LEFT[0] + SPACE[0], TOP_LEFT[1] + SPACE[1])
    LABEL_OFFSET = (1, 1)
    LABEL_SIZE = (26, 40)


def defaulted_screenshot():
    return Screenshot(Info.TOP_LEFT, Info.BOTTOM_RIGHT, Info.SPACING, Info.LABEL_OFFSET, Info.LABEL_SIZE)


def train_from_default():
    # Construct a screenshot read for this image.
    scrn = defaulted_screenshot()
    scrn.load(TRAINING_IMAGE)
    images = scrn.map_to_images(TRAINING_DECK)
    return images
