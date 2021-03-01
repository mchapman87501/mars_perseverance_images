#!/usr/bin/env python3
"""
Create or update an image database in the current working dir.
"""

import json
from pathlib import Path

from band_finder.rss_feed import get_rqst_params, get_img_metadata
from band_finder.image_db import ImageDB


def main():
    """Mainline for standalone execution."""
    db = ImageDB()

    page = 1
    while True:
        params = get_rqst_params(page=page, num=1000)
        json_info = get_img_metadata(params)
        Path(f"rss_feed_{page}.json").write_text(
            json.dumps(json_info, indent=4))
        records = json_info["images"]
        if not records:
            break
        db.add_or_update(records)
        print(f"Page {page}: added {len(records)} records.")
        page += 1


if __name__ == "__main__":
    main()
