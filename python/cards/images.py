from . cards import Cards, Faces, Suites
import cv2
import logging
import numpy as np


def display(*images):
    """ Display a series of one or more OpenCV images and wait for a keypress. """

    for n, image in enumerate(images, 1):
        cv2.imshow("Image"+str(n), image)

    cv2.waitKey(0)

    cv2.destroyAllWindows()


def preprocess(image):
    """Returns a grayed, blurred, and adaptively thresholded camera image."""
    # https://github.com/EdjeElectronics/OpenCV-Playing-Card-Detector/blob/master/Cards.py

    if len(image.shape) > 2 and image.shape[2] > 1:
        image= cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(image, (5, 5), 0)

    # The best threshold level depends on the ambient lighting conditions.
    # For bright lighting, a high threshold must be used to isolate the cards
    # from the background. For dim lighting, a low threshold must be used.
    # To make the card detector independent of lighting conditions, the
    # following adaptive threshold method is used.
    #
    # A background pixel in the center top of the image is sampled to determine
    # its intensity. The adaptive threshold is set at 50 (THRESH_ADDER) higher
    # than that. This allows the threshold to adapt to the lighting conditions.
    img_w, img_h = np.shape(image)[:2]
    bkg_level = image[int(img_h / 100)][int(img_w / 2)]
    thresh_level = bkg_level + 60

    _, thresh = cv2.threshold(blur, thresh_level, 255, cv2.THRESH_BINARY)

    return thresh


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
        self.labels = None

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
            base_image  = cv2.cvtColor(base_image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(base_image, (3, 3), 2)
        blurthresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_TOZERO + cv2.THRESH_OTSU)
        self.thresholded = cv2.adaptiveThreshold(blurthresh, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        # Crop to the card space.
        (tlx, tly), (brx, bry) = self.space
        base_image = base_image[tly:bry, tlx:brx]

        (card_w, card_h), ((off_x, off_y), (label_w, label_h)) = self.spacing, self.face
        columns, rows = self.src_shape[0], self.src_shape[1]
        labels = [None] * Cards.COUNT

        for card_no in range(Cards.COUNT):
            card_x, card_y = int(card_no % columns), int(card_no / columns)
            src_x = card_w * card_x + off_x
            src_y = card_h * card_y + off_y

            labels[card_no] = base_image[src_y:src_y+label_h, src_x:src_x+label_w]

        self.labels = labels

    def map_to_deck(self, deck):
        """
        Reorder labels based on the order of the cards in 'deck'.

        :param deck: list of face representations (e.g AS for ace of spaces).
        :return:
        """
        if self.labels is None:
            raise RuntimeError("No cards loaded")

        # Iterate across the card-labels in 'deck' and find the card index of each label,
        # then move the label image into the ordered position.
        ordered = [None] * Cards.COUNT
        for card_no in range(Cards.COUNT):
            card = deck[card_no]
            try:
                card_index = Cards.index(card)
            except ValueError:
                raise ValueError("Unrecognized card in deck: " + card)

            ordered[card_index] = self.labels[card_no]

        # Validate there are the correct number of images.
        if sum(1 for i in range(Cards.COUNT) if ordered[i] is None):
            raise RuntimeError("One or more card images missing.")

        return ordered

    def calculate_deck(self, from_labels):
        """
        Attempt to identify the cards in a Screenshot previously loaded images.

        :param filename: [optional] Screenshot to analyze.
        :return: the cards in l->r, t->b order.
        """
        if self.labels is None:
            raise RuntimeError("Must load an image with/before generate_deck.")

        deck = []
        for label_no, label in enumerate(self.labels, 0):
            index = None
            for candidate_no in range(len(from_labels)):
                if not np.array_equal(label, from_labels[candidate_no]):
                    l, r = process(label), process(from_labels[candidate_no])
                    img = np.zeros((l.shape[0], l.shape[1]*2), dtype=np.uint8)
                    img[:, :l.shape[1]] = l
                    img[:, l.shape[1]:] = r
                    display(img)
                    if not np.array_equiv(l, r):
                        continue
                index = candidate_no
                break
            if index is None:
                logging.warning("Unidentified card[%d]" % label_no)
                continue
            card = Cards.INDEX[index]
            if card in deck:
                raise RuntimeError("Duplicate detections of card: " + card)
            deck.append(card)

        if len(deck) != len(self.labels):
            raise RuntimeError("Missing cards")

        return deck
