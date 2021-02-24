#!/usr/bin/env python3
"""
Try to identify sets of images that constitute a single RGB image.
Copyright 2021, Mitch Chapman  All rights reserved
"""

from dataclasses import dataclass

from PIL import Image
import imagehash

from band_finder.image_db import ImageDB
from band_finder.image_cache import ImageCache


class ImageWithHash:
    def __init__(self, image_record, image):
        self._record = image_record
        self._img = image
        self._hash = imagehash.average_hash(image)

    def image_id(self):
        return self._record["image_id"]

    def diff(self, other):
        return self._hash - other._hash

    def __lt__(self, other):
        return self.diff(other) < 0

    def __eq__(self, other):
        return self.diff(other) == 0

    def __gt__(self, other):
        return self.diff(other) > 0


class ImageComponents:
    def __init__(self, red_hash, images_by_rgb):
        """Given a red image, find most similar green and blue.

        Args:
            red_hash (ImageWithHash): the red image to match
            images_by_rgb (dict): dictionary mapping "R", "G", "B" to
                                  lists of ImageWithHash.
        """
        self._red = red_hash
        self._green = self._nearest(self._red, images_by_rgb["G"])
        self._blue = self._nearest(self._red, images_by_rgb["B"])

        # TODO determine whether or not good matches were found.

    def _nearest(self, src_image, images):
        by_distance = []
        for other in images:
            by_distance.append((src_image.diff(other), other))
        return min(by_distance)[-1]

    def combined(self):
        """Get a full RGB derived from images best matching self's red image.

        Returns:
            PIL.Image: the combined image.
        """
        [red_band, green_band, blue_band] = [
            iwh._img for iwh in [self._red, self._green, self._blue]
        ]
        channels = [
            red_band.getchannel("R"),
            green_band.getchannel("G"),
            blue_band.getchannel("B")
        ]
        return Image.merge("RGB", channels)


def main():
    """Mainline for standalone execution."""

    # Assume an image database exists in the current working directory.
    db = ImageDB()
    cache = ImageCache(db)

    # How expensive can this be? :)
    # Group images by (guessed) color component.
    # Use image hashes to estimate the most similar images across all
    # color components.

    # How to generalize this?  navcam-right image IDs start with
    # "NR[RGBEM]".  I think "M" are thumbnails.  I don't know what "E" are.
    images_by_rgb = dict(R=[], G=[], B=[], E=[], M=[])

    camera = "NAVCAM_RIGHT"
    records = list(db.images_for_camera(camera))
    for record in records:
        # Assume the color component is embedded in the image_id:
        image_id = record["image_id"]
        component = image_id[2]
        if component in "RGB":
            image = cache.get_image(image_id)
            images_by_rgb[component].append(ImageWithHash(record, image))

    for image_with_hash in images_by_rgb["R"]:
        img_comp = ImageComponents(image_with_hash, images_by_rgb)
        combined = img_comp.combined()

        img_id = image_with_hash.image_id()
        filename = f"NRRGB_{img_id[4:]}.png"
        combined.save(filename)


if __name__ == "__main__":
    main()
