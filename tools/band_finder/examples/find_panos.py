#!/usr/bin/env python3
"""
Suss out how to identify NAVCAM images that constitute
a panorama.
"""

from pathlib import Path
import re
import traceback

import cv2
from PIL import Image
import numpy as np

from band_finder.image_db import ImageDB
from band_finder.image_cache import ImageCache
from band_finder.tile_brightness_matcher import TileBrightnessMatcher


class PanoImageInfo:
    def __init__(self, image_id, img, rect):
        self.image_id = image_id
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
            image_id = rec["image_id"]
            img = image_cache.get_image(image_id)
            rect = self._get_rect(rec)
            yield PanoImageInfo(image_id, img, rect)

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


class PanoFinder:
    _tuple_expr = re.compile(r"^\((?P<fields>([\d.+-]+,?)+)\)")

    def __init__(self, db):
        self._db = db

    def _gen_cam_images(self, which_cam):
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
        WHERE cam_instrument = ?
          AND sample_type = 'Full'
          AND ext_scale_factor = 1.0
          AND x NOT NULL
          AND y NOT NULL
          AND w NOT NULL
          and h NOT NULL
        ORDER BY site, drive, ext_sclk, image_id
        """
        to_tuple = self._as_num_tuple
        for row in self._db.cursor().execute(query, (which_cam,)):
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


class PanoStitcher:
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
        for img_set in self._get_pano_image_sets():
            full_name = f"{img_set.name()}_{self._which_cam}"
            print("Building", full_name)
            try:
                pano = self._build_image(img_set)
                pano.save(outdir / f"{full_name}.png")
            except Exception as info:
                traceback.print_exc()
                print(f"Failed building {full_name}: {info}")

    def _build_image(self, img_set):
        img_info = list(img_set.gen_images(self._cache))
        img_rect = img_set.rect()
        size = tuple(img_rect[2:])

        matcher = TileBrightnessMatcher()
        for rec in img_info:
            img_rect = rec.rect[:2]
            rgb_image = self._prepare_tile_image(rec)
            matcher.add(rgb_image, origin=rec.rect[:2])

        result = matcher.composite()
        return result

    def _prepare_tile_image(self, rec):
        # This assumes the image needs to be demosaiced - but that is
        # true only if the metadata's image_id has "E" as its third 
        # character.
        #
        # "F" images appear to be already de-mosaiced.
        if rec.image_id[2:3] == "F":
            return rec.img

        tile_img = rec.img
        # Cop out - use someone else's demosaicing algorithms.
        # https://gist.github.com/bbattista/8358ccafecf927ae1c58c944ab470ffb
        bayer = np.asarray(tile_img.convert("L"), dtype=np.uint16)
        demosaic = cv2.cvtColor(bayer, cv2.COLOR_BAYER_BG2RGB)
        demo8bit = demosaic.astype(np.uint8)
        return Image.fromarray(demo8bit)


def main():
    """Mainline for standalone execution."""
    db = ImageDB()
    for cam in db.cameras():
        stitcher = PanoStitcher(db, cam)
        stitcher.build_all()


if __name__ == "__main__":
    main()
