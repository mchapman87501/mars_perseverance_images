#!/usr/bin/env python3
"""
Cache all images taken with an "RGB" camera filter.
Copyright 2021, Mitch Chapman  All rights reserved
"""

from band_finder.image_db import ImageDB
from band_finder.image_cache import ImageCache
import datetime


def main():
    """Mainline for standalone execution."""

    # Assume an image database exists in the current working directory.
    db = ImageDB()
    cache = ImageCache(db)

    query = (
        "SELECT image_id FROM Images"
        " WHERE camera_filter LIKE '%RGB%'"
        " AND sample_type = 'Full'"
    )
    cursor = db.cursor()
    for row in cursor.execute(query):
        print("Caching", row["image_id"])
        cache.get_image(row["image_id"])


if __name__ == "__main__":
    main()
