#!/usr/bin/env python3
"""
Suss out how to identify NAVCAM images that constitute
a panorama.
"""

import re

import cv2
from PIL import Image
import numpy as np

from band_finder.image_db import ImageDB
from band_finder.image_cache import ImageCache


# TODO use type annotations and datarecord.
class PanoImageInfo:
    def __init__(self, img, rect):
        self.img = img
        self.rect = rect


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
            image_frect = (rec["x"] - 1, rec["y"] - 1, rec["w"], rec["h"])
            image_rect = tuple(int(f) for f in image_frect)
            img = image_cache.get_image(rec["image_id"])
            yield PanoImageInfo(img, image_rect)

    def name(self):
        return self._name

    def rect(self):
        x0 = y0 = xf = yf = 0
        for rec in self._records:
            # Metadata origin is at (1, 1).
            x, y = rec["x"] - 1, rec["y"] - 1
            x0 = min(x0, x)
            y0 = min(y0, y)
            xf = max(xf, x + rec["w"])
            yf = max(yf, y + rec["h"])
        return (int(x0), int(y0), int(xf - x0), int(yf - y0))


class PanoFinder:
    _tuple_expr = re.compile(r"^\((?P<fields>([\d.+-]+,?)+)\)")

    def __init__(self, db):
        self._db = db

    def _left_navcam_images(self):
        return list(self._gen_left_navcam_images())

    def _gen_left_navcam_images(self):
        query = """
        SELECT
          site, drive, ext_sclk,
          -- cam_model_component_list,
          -- cam_position,
          -- date_taken_utc,
          -- attitude,
          -- ext_mast_azimuth, ext_mast_elevation,
          -- ext_scale_factor,
          -- ext_x, ext_y, ext_z,
          ext_sf_left x, ext_sf_top y,
          ext_sf_width w, ext_sf_height h,
          -- ext_width, ext_height,
          image_id
        FROM Images
        WHERE cam_instrument = 'NAVCAM_LEFT'
          AND sample_type = 'Full'
          AND ext_scale_factor = 1.0
        ORDER BY site, drive, ext_sclk, image_id
        """
        to_tuple = self._as_num_tuple
        for row in self._db.cursor().execute(query):
            result = dict((key, row[key]) for key in row.keys())
            # result['cam_position'] = to_tuple(row['cam_position'])
            # result['attitude'] = to_tuple(row['attitude'])
            # result['date_taken_utc'] = row['date_taken_utc'].isoformat()
            yield result

    def _as_num_tuple(self, value_str):
        # pycodestyle does not understand walrus?
        if m := self._tuple_expr.match(value_str):
            fields = [float(f) for f in m.group("fields").split(",")]
            return tuple(fields)
        return value_str

    def gen_image_sets(self):
        prev_sclk = None
        curr_set = []
        for record in self._gen_left_navcam_images():
            sclk = record["ext_sclk"]
            if sclk != prev_sclk:
                if len(curr_set) > 1:
                    yield curr_set
                curr_set = []
                prev_sclk = sclk
            curr_set.append(record)
        if len(curr_set) > 1:
            yield curr_set


class PanoStitcher:
    """
    PanoStitcher assembles a panorama from a given set of image records.
    It positions constituent images based on their ext_sf_* coords.

    Initial implementation does not care whether the source images are
    color components or full raster readouts.
    """
    def __init__(self, db):
        self._db = db
        self._finder = PanoFinder(db)
        self._cache = ImageCache(db)

    def _get_pano_image_sets(self):
        return [
            PanoImageSet.from_records(recs)
            for recs in self._finder.gen_image_sets()
        ]

    def build_all(self):
        for img_set in self._get_pano_image_sets():
            print("Building", img_set.name())
            pano = self._build_image(img_set)
            pano.save(f"{img_set.name()}.png")

    def _build_image(self, img_set):
        img_info = list(img_set.gen_images(self._cache))
        img_rect = img_set.rect()
        print("  Image", img_rect)
        size = tuple(img_rect[2:])
        result = Image.new("RGB", size)
        for rec in img_info:
            tile_img = self._prepare_tile_image(rec.img)
            dest_rect = rec.rect
            print("  Tile", dest_rect)
            # XXX FIX THIS should use the full dest_rect.
            dest_origin = dest_rect[:2]
            result.paste(tile_img, dest_origin)
        return result

    def _prepare_tile_image(self, tile_img):
        # Cop out - use someone else's demosaicing algorithms.
        # https://gist.github.com/bbattista/8358ccafecf927ae1c58c944ab470ffb
        bayer = np.asarray(tile_img.convert("L"), dtype=np.uint16)
        demosaic = cv2.cvtColor(bayer, cv2.COLOR_BAYER_BG2RGB)
        demo8bit = demosaic.astype(np.uint8)
        return Image.fromarray(demo8bit)


def main():
    """Mainline for standalone execution."""
    db = ImageDB()
    stitcher = PanoStitcher(db)
    stitcher.build_all()


if __name__ == "__main__":
    main()
