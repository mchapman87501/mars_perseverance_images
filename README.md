This is a hodgepodge of notes and scripts for working with
Mars 2020 Mission Perseverance Rover [raw images](https://mars.nasa.gov/mars2020/multimedia/raw-images/).  It's a mess!

# tools/band_finder

`tools/band_finder` contains a Python package that can
* store image metadata from the raw images RSS feed in an SQLite database 
* perform queries thereon
* create a local cache of raw images

You may be able to build and install the package.  As this is really a pile of exploratory hacks I'd recommend using it in situ, or installing it as an editable package inside a Python venv.

# tools/band_finder/examples

These started out as unit tests ;)  But this is a pile of exploratory hacks.  I'd recommend doing the following:

1. Make sure you can import the `band_finder` package
2. cd into the `examples` directory
3. `python populate_db.py` to create a local database of image metadata
4. `python auto_create_rgbs.py` to automatically assemble color images from
   the right Navcam.

It probably won't work, but maybe the source code will offer clues for your own explorations.  Have fun!


