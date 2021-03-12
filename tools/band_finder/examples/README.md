# Examples, Or, What's All This?

It's a mess, that's what it is!

## Prerequisites

All of these command-line scripts require the `band_finder` package to be on your PYTHONPATH.  You might be able to install it as a package by running `python -m pip install .` in the parent directory.  I've been using `python -m pip install -e .`, after activating a Python 3.9 venv.

## populate_db.py

Use `python populate_db.py` to create an SQLite database, in the current working directory, containing some juicy image metadata from the Perseverance raw images RSS feed.  If the database already exists, this script will update it with the latest info from the feed.

## get_rgb_images.py

After you've used `populate_db.py` to create a database, `python get_rgb_images.py` will download all images listed in the database whose camera filter appears to be an RGB filter.

The script downloads the images to the `image_cache` directory in the current working directory.

## find_panos.py

This script finds images which appear to be tiles of larger, composite images, and it reassembles them to recreate the composite images.  It places the composites in a `panoramas` subdirectory, so named because I didn't understand that these were not necessarily panoramas.

`find_panos.py` faces some challenges.  The individual tile images are supposed to have come from a single "exposure" of the full sensor, but as Emily Lakdawalla has explained, some may have been processed - in particular, their contrast may have been adjusted - before being recorded.

When re-assembling composite images `find_panos.py` tries to adjust the tile images to have consistent tonal ranges.  To do this it takes advantage of the fact that the tile images overlap a bit, by about 16 rows/columns of pixels.  It uses these overlapping image rectangles to create a mapping from one tile image to another.

(Because I am lazy and inept) the script first de-mosaics the tile images as necessary, then converts them to a colorspace (L\*a\*b\*) in which one of the color components represents pixel brightness.  Then, for each colorspace channel, it creates the aforementioned mappings.  Finally, it uses numpy's `interp` function together with the mappings to adjust all of the pixels of each new tile image, to better match already-composited tiles.

The overlapping image rectangles may not cover the entire tonal range of their respective tiles.  To help `interp` adjust pixels that lie outside the range of values in the overlapping rectangles, the channel mappings are initialized with default, 1:1 mappings of the extrema of each channel.

Despite being simple-minded, this approach works pretty well.  It does fail miserably when some image tiles are incomplete, as was true for some images produced early in the Perseverance mission.

