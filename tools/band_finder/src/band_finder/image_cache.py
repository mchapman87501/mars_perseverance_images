#!/usr/bin/env python3
"""
image_cache caches Mars Perseverance images locally.
Copyright 2021, Mitch Chapman  All rights reserved
"""

import io
from pathlib import Path

from PIL import Image
import requests


class ImageCache:
    # Image cache directory is relative to current working dir.
    _cache_dir = Path("image_cache")

    def __init__(self, db):
        """Initialize a new instance.

        Args:
            db (image_db.ImageDB): Database of image metadata.
        """
        self._db = db

    def get_image(self, image_id):
        result = self._image_from_cache(image_id)
        if result is None:
            result = self._retrieve_image(image_id)
        return result

    def _retrieve_image(self, image_id):
        query = "SELECT full_res_url FROM Images WHERE image_id=?"
        cursor = self._db.cursor()
        for row in cursor.execute(query, (image_id,)):
            url = row[0]
            req = requests.get(url, allow_redirects=True)
            req.raise_for_status()

            img_data_io = io.BytesIO(req.content)
            out_path = self._cached_path(image_id)
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(img_data_io.read())
            return Image.open(out_path)

    def _image_from_cache(self, image_id):
        img_path = self._cached_path(image_id)
        if img_path.exists():
            # TODO Figure out the correct mode (RGB, single color)
            # in which to open the image.
            return Image.open(img_path)
        return None

    def _cached_path(self, image_id):
        return self._cache_dir / f"{image_id}.png"
