#!/usr/bin/env python3
"""
Combine a set of single-color images.
Copyright 2021, Mitch Chapman  All rights reserved
"""

import argparse
import datetime
from PIL import Image

from band_finder.image_db import ImageDB
from band_finder.image_cache import ImageCache


def _get_opt_channel(pathname, channel):
    # Get the specified ('R', 'G', 'B') channel from an image file.
    # If pathname is None, return None.  Otherwise return the channel.
    if pathname is not None:
        # Assume grayscale RGB
        return Image.open(pathname).getchannel(channel)
    return None


def _channel_or_default(chan, size):
    if chan is not None:
        return chan
    return Image.new("L", size)


def _combine_images(rpathname, gpathname, bpathname):
    red = _get_opt_channel(rpathname, "R")
    green = _get_opt_channel(gpathname, "G")
    blue = _get_opt_channel(bpathname, "B")

    valids = [chan for chan in [red, green, blue] if chan is not None]
    sizes = set(chan.size for chan in valids)
    if not sizes:
        raise SystemExit("At least one color image must be specified")
    if len(sizes) != 1:
        raise SystemExit(f"Images have different sizes: {sizes}")
    size = sizes.pop()

    red = _channel_or_default(red, size)
    green = _channel_or_default(green, size)
    blue = _channel_or_default(blue, size)

    return Image.merge("RGB", [red, green, blue])


def parse_cmdline():
    parser = argparse.ArgumentParser(description="Combine a set of single-color images")
    # TODO figure out how to handle specialized band-pass colors - should
    # be able to deduce from image metadata.
    parser.add_argument("-r", "--red", type=str, help="red image")
    parser.add_argument("-g", "--green", type=str, help="green image")
    parser.add_argument("-b", "--blue", type=str, help="blue image")
    parser.add_argument("output_filename", help="Where to store the combined image.")

    result = parser.parse_args()
    imgs = [result.red, result.green, result.blue]
    if imgs == [None, None, None]:
        parser.error("At least one of -r, -g, -b must be specified")
    return result


def main():
    """Mainline for standalone execution."""

    # Assume an image database exists in the current working directory.
    db = ImageDB()
    cache = ImageCache(db)

    opts = parse_cmdline()

    result_img = _combine_images(opts.red, opts.green, opts.blue)
    result_img.save(opts.output_filename)


if __name__ == "__main__":
    main()
