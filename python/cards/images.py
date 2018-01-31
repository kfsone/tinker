from . cards import Cards, Faces, Suites
import cv2
import numpy as np


def display(*images):
    """ Display a series of one or more OpenCV images and wait for a keypress. """

    for n, image in enumerate(images, 1):
        cv2.imshow("Image"+str(n), image)

    cv2.waitKey(0)

    cv2.destroyAllWindows()


class Screenshot(object):

    def __init__(self, top_left, bottom_right, spacing, face_offset, face_size):
        """
        Constructs a screenshot processor for screenshots of a given layout.

        The image will be converted to greyscale, cropped (top_left, bottom_right)
        and then face representations will be extracted based on spacing and the
        face offset and size.

        Size represents how much of each face will be looked at and is usually just
        the small top-left corner, e.g (offset=(0,0), size=(32,48)).

        :param top_left: Point (x,y) of the card space.
        :param bottom_right: Point (x,y) of the card space.
        :param spacing: Distance (w, h) between card labels.
        :param face_offset: Offset from the top-left (w, h) of the face.
        :param face_size: Width and height of the face itself.
        """
        # Validation
        space_dim = np.array(bottom_right, dtype=np.int) - top_left
        if any(space_dim <= 0):
            raise ValueError("Invalid top_left/bottom_right.")

        spacing = np.array(spacing, dtype=np.int)
        face_offset = np.array(face_offset, dtype=np.int)
        face_size = np.array(face_size, dtype=np.int)
        if any(face_offset + face_size > space_dim):
            raise ValueError("Face positions exceed bounds of card space.")

        self.space = (top_left, bottom_right)
        self.spacing = spacing
        self.face = (face_offset, face_size)

        self.src_shape = space_dim[0] / spacing[0], space_dim[1] / spacing[1]
        self.src_shape = int(self.src_shape[0]), int(self.src_shape[1])
        self.shape = (Suites.COUNT, Faces.COUNT)
        self.base_image = None
        self.images = None

    def load(self, filename):
        """
        Load the specified screenshot for processing.

        :param filename: Path/filename of the screenshot to load.
        """
        base_image = cv2.imread(filename)
        if base_image is None:
            raise IOError("Cannot open image: " + filename)
        if base_image.shape[1] < self.spacing[0] or base_image.shape[0] < self.spacing[1]:
            raise ValueError("Image is smaller than card space dimensions.")

        # Ensure greyscale
        if len(base_image.shape) > 2 and base_image.shape[2] > 1:
            base_image = cv2.cvtColor(base_image, cv2.COLOR_BGR2GRAY)

        # Crop to the card space.
        (tlx, tly), (brx, bry) = self.space
        self.base_image = base_image[tly:bry, tlx:brx]
        self.images = None

    def _foreach_src_image(self):
        """ Helper: Yield the card number and source for each card in the screenshot. """
        base_image = self.base_image
        spacing, (face_offset, face_shape) = self.spacing, self.face
        columns, rows = self.src_shape[0], self.src_shape[1]

        for card_no in range(Cards.COUNT):
            tlx = spacing[0] * int(card_no % columns) + face_offset[0]
            tly = spacing[1] * int(card_no / columns) + face_offset[1]
            p1 = (tlx, tly)
            p2 = (tlx + face_shape[0], tly + face_shape[1])
            yield card_no, base_image[p1[1]:p2[1], p1[0]:p2[0]]

    def map_to_images(self, deck):
        """
        Identifies the images in the loaded base_image as being the cards
        listed in the given deck. This populates the .images object,
        which can then be used to recognize the cards in a different image.

        :param deck: list of face representations (e.g AS for ace of spaces).
        :return:
        """
        if self.base_image is None:
            raise RuntimeError("No card images loaded")

        processed = set()
        self.images = np.ndarray((Cards.COUNT, self.face[1][1], self.face[1][0]), dtype=np.uint8)
        for card_no, image in self._foreach_src_image():
            card = deck[card_no]
            try:
                card_index = Cards.index(card)
            except ValueError:
                raise ValueError("Unrecognized card in deck: " + card)

            self.images[card_index] = image

            processed.add(card_index)

        # Validate there are the correct number of images.
        if len(processed) != len(deck):
            raise RuntimeError("One or more card images missing.")

        return self.images

    def generate_deck(self, filename=None):
        """
        Loads a screenshot and attempts to identify the cards in it using the previously
        populated "images" index.

        :param filename: [optional] Screenshot to analyze.
        :return: the cards in l->r, t->b order.
        """
        if filename:
            self.load(filename)
        if self.base_image is None:
            raise RuntimeError("Must load an image with/before generate_deck.")
        if self.images is None:
            raise RuntimeError("Must load or map images before calling generate_deck.")

        deck = []
        card_images = list((idx, img) for idx, img in enumerate(self.images, 0))
        for _, src_image in self._foreach_src_image():
            for candidate_index in range(len(card_images)):
                card_index, card_image = card_images[candidate_index]
                if not np.array_equal(card_image, src_image):
                    continue
                card = Cards.INDEX[card_index]
                if card in deck:
                    raise RuntimeError("Duplicate detections of card: " + card)
                deck.append(card)
                # Remove this from the candidacy
                card_images.pop(candidate_index)
                break

        return deck

