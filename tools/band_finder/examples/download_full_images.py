#!/usr/bin/env python3
"""
Download (cache) images that appear to be full-res color images.
Copyright (c) 2021 Mitch Chapman  All rights reserved
"""

from band_finder.image_db import ImageDB
from band_finder.image_cache import ImageCache


def main():
    db = ImageDB()
    cache = ImageCache(db)
    query = "SELECT image_id FROM Images where image_id like '__F%'"
    for row in db.cursor().execute(query):
        image_id = row[0]
        print(image_id)
        cache.get_image(image_id)


if __name__ == "__main__":
    main()
