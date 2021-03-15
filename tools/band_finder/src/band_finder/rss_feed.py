#!/usr/bin/env python3
"""
Retrieve metadata about available images.

This code derives from two sources:
https://github.com/kmgill/cassini_processing/blob/master/fetch_m20_raw.py

https://colab.research.google.com/drive/1SqTzhMo5NeVNZ6YTwsSpsssLH3vp5vX_?usp=sharing
[by Robert Cadena](https://twitter.com/robertcadena/)

Copyright 2021, Mitch Chapman  All rights reserved
"""

import requests

# This is almost verbatim from fetch_m20_raw.py.
INSTRUMENTS = {
    "HAZ_FRONT": [
        "FRONT_HAZCAM_LEFT_A",
        "FRONT_HAZCAM_LEFT_B",
        "FRONT_HAZCAM_RIGHT_A",
        "FRONT_HAZCAM_RIGHT_B",
    ],
    "HAZ_REAR": ["REAR_HAZCAM_LEFT", "REAR_HAZCAM_RIGHT"],
    "NAVCAM": ["NAVCAM_LEFT", "NAVCAM_RIGHT"],
    "MASTCAM": ["MCZ_LEFT", "MCZ_RIGHT"],
    "EDLCAM": ["EDL_DDCAM", "EDL_PUCAM1", "EDL_PUCAM2", "EDL_RDCAM", "EDL_RUCAM", "LCAM"],
    # I don't know how these values should be grouped. I just noticed them from a
    # full, unfiltered RSS feed download.
    "OTHER": ["SHERLOC_WATSON", "SKYCAM"]
}


def get_search_param(cameras):
    if cameras is not None:
        usecams = []
        for cam in cameras:
            if cam in INSTRUMENTS:
                for c in INSTRUMENTS[cam]:
                    usecams.append(c)
            else:
                usecams.append(cam)
        return "|".join(usecams)
    return None


def get_rqst_params(cameras=None, minsol=None, maxsol=None, num=10, page=1):
    result = {
        "feed": "raw_images",
        "category": "mars2020",
        "feedtype": "json",
        "num": num,
        "page": page - 1,
        "order": "sol desc",
    }

    search = get_search_param(cameras)
    if search is not None:
        result["search"] = search

    if minsol is not None:
        result["condition_2"] = f"{minsol}:sol:gte"
    if maxsol is not None:
        result["condition_3"] = f"{maxsol}:sol:lte"

    return result


def get_img_metadata(search_params):
    req = requests.get(
        "https://mars.nasa.gov/rss/api/",
        params=search_params,
        allow_redirects=True,
    )

    if req.status_code != 200:
        raise SystemExit(
            "Error fetching search results.  "
            f"HTTP status code {req.status_code}"
        )

    return req.json()
