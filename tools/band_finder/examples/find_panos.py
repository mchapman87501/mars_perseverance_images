#!/usr/bin/env python3
"""
Suss out how to identify NAVCAM images that constitute
a panorama.
"""

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import re
import traceback

import numpy as np
from skimage import io, color
from skimage.util import img_as_ubyte

from band_finder.image_db import ImageDB
from band_finder.image_cache import ImageCache
from band_finder.tile_matcher import TileMatcher
from band_finder.bayer_to_rgb import bayer_to_rgb


class PanoImageInfo:
    def __init__(self, image_id, image, rect):
        self.image_id = image_id
        self.image = image
        self.rect = rect

    def is_bayer(self):
        # Images whose image_id has "E" as its third character
        # are raw sensor readouts that need to be de-mosaiced.
        return self.image_id[2:3] == "E"


class PanoImageSet:
    @classmethod
    def from_records(cls, records):
        result = cls()
        for rec in records:
            result.add_record(rec)
        return result

    def __init__(self):
        self._name = "pano_empty"
        self._drive = None
        self._site = None
        self._sclk = None
        self._records = []

    def add_record(self, rec):
        if not self._records:
            drive = self._drive = rec["drive"]
            site = self._site = rec["site"]
            sclk = self._sclk = rec["ext_sclk"]
            self._name = f"pano_{drive}_{site}_{sclk}"
        self._records.append(rec)

    def gen_images(self, image_cache):
        for rec in self._records:
            # Metadata origin is at (1, 1).
            image_id = rec["image_id"]
            image = image_cache.get_image(image_id)
            rect = self._get_rect(rec)
            yield PanoImageInfo(image_id, image, rect)

    def name(self):
        return self._name

    def rect(self):
        x0 = y0 = xf = yf = 0
        for rec in self._records:
            x, y, w, h = self._get_rect(rec)
            x0 = min(x0, x)
            y0 = min(y0, y)
            xf = max(xf, x + rec["w"])
            yf = max(yf, y + rec["h"])
        return (int(x0), int(y0), int(xf - x0), int(yf - y0))

    def _get_rect(self, rec):
        x, y, w, h = rec["x"], rec["y"], rec["w"], rec["h"]
        # Metadata origin is at (1, 1).
        return tuple([int(f) for f in (x - 1, y - 1, w, h)])


class PanoStitcher:
    """
    PanoStitcher stitches a single PanoImageSet.
    """
    def __init__(self):
        self._db = ImageDB()
        self._cache = ImageCache(self._db)

    def build_image(self, image_set):
        """Build a panoramic image from a set of image tiles.

        Args:
            image_set (PanoImageSet): the set of images to stitch together

        Returns:
            np.array: The panorama image
        """
        pano_tiles = list(image_set.gen_images(self._cache))

        matcher = TileMatcher(image_set.name())
        # is_bayer = False
        for rec in pano_tiles:
            bmsg = "(bayer)" if rec.is_bayer else ""
            print(f"Tile {rec.image_id} {rec.rect} {bmsg}")
            image = bayer_to_rgb(rec.image) if rec.is_bayer() else rec.image
            # Work in Lab color.
            image = color.rgb2lab(image)
            matcher.add(image, origin=rec.rect[:2])

        composite = matcher.composite()
        result = img_as_ubyte(color.lab2rgb(self._rescaled(composite)))
        return result

    def _rescaled(self, image):
        # Rescale image data as necessary to fit within the Lab
        # colorspace.
        result = image.copy()
        # From one of the scikit-image maintainers (I think):
        # https://stackoverflow.com/a/28048090
        # https://github.com/scikit-image/scikit-image/issues/1185
        for chan, cmin, cmax, stretch in [
            [0, 0.0, 100.0, True],
            [1, -127.0, 128.0, False],
            [2, -128.0, 127.0, False],
        ]:
            self._rescale_channel(result, chan, cmin, cmax, stretch)
        return result

    def _rescale_channel(self, image, channel, min_valid, max_valid, stretch):
        values = image[:, :, channel]
        max_in = np.max(values)
        min_in = np.min(values)

        if stretch or ((max_in > max_valid) or (min_in < min_valid)):
            d_in = max_in - min_in
            d_out = max_valid - min_valid
            scale = d_out / d_in
            values = (values - min_in) * scale + min_valid
            image[:, :, channel] = values


class PanoFinder:
    _tuple_expr = re.compile(r"^\((?P<fields>([\d.+-]+,?)+)\)")

    def __init__(self, db):
        self._db = db

    def _gen_cam_images(self, which_cam):
        query = """
        SELECT
          site, drive, ext_sclk,
          ext_sf_left x, ext_sf_top y,
          ext_sf_width w, ext_sf_height h,
          image_id
        FROM Images
        WHERE cam_instrument = ?
          AND sample_type = 'Full'
          AND ext_scale_factor = 1.0
          AND x NOT NULL
          AND y NOT NULL
          AND w NOT NULL
          and h NOT NULL
        ORDER BY site, drive, ext_sclk, image_id
        """
        for row in self._db.cursor().execute(query, (which_cam,)):
            result = dict((key, row[key]) for key in row.keys())
            # result['cam_position'] = to_tuple(row['cam_position'])
            # result['attitude'] = to_tuple(row['attitude'])
            # result['date_taken_utc'] = row['date_taken_utc'].isoformat()
            yield result

    def gen_image_sets(self, which_cam):
        prev_sclk = None
        curr_set = []
        for record in self._gen_cam_images(which_cam):
            sclk = record["ext_sclk"]
            if sclk != prev_sclk:
                if len(curr_set) > 1:
                    yield curr_set
                curr_set = []
                prev_sclk = sclk
            curr_set.append(record)
        if len(curr_set) > 1:
            yield curr_set


def stitch_set(args):
    """
    Stitch an image set.
    This is intended for use with multiprocessing, or with a
    concurrent.futures Exector.

    Args:
        args: a tuple of (image set, camera name, output directory)
    """
    try:
        image_set, cam, outdir = args
        full_name = f"{image_set.name()}_{cam}"

        print("Building", full_name)

        stitcher = PanoStitcher()
        pano = stitcher.build_image(image_set)
        io.imsave(outdir / f"{full_name}.png", pano)
    except Exception as info:
        traceback.print_exc()
        print(f"Failed stitching set: {info}")


class CamPanoStitcher:
    """
    PanoStitcher assembles a panorama from a given set of image records.
    It positions constituent images based on their ext_sf_* coords.

    Initial implementation does not care whether the source images are
    color components or full raster readouts.
    """

    def __init__(self, db, which_cam):
        self._db = db
        self._which_cam = which_cam
        self._finder = PanoFinder(db)
        self._cache = ImageCache(db)

    def _get_pano_image_sets(self):
        return [
            PanoImageSet.from_records(recs)
            for recs in self._finder.gen_image_sets(self._which_cam)
        ]

    def build_all(self):
        outdir = Path("panoramas")
        outdir.mkdir(exist_ok=True, parents=True)

        cam = self._which_cam
        image_sets = self._get_pano_image_sets()

        args = [(image_set, cam, outdir) for image_set in image_sets]
        print("Number of image sets:", len(args))
        with ProcessPoolExecutor() as executor:
            executor.map(stitch_set, args)
        print("Done processing image sets.")


def main():
    """Mainline for standalone execution."""
    db = ImageDB()
    for cam in db.cameras():
        cam_stitcher = CamPanoStitcher(db, cam)
        cam_stitcher.build_all()


if __name__ == "__main__":
    main()
