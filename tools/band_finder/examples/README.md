# Examples, Or, What's All This?

It's a mess, that's what it is!

## Prerequisites

All of these command-line scripts require the `band_finder` package to be on your PYTHONPATH.  You might be able to install it as a package by running `python -m pip install .` in the parent directory.  I've been using `python -m pip install -e .`, after activating a Python 3.9 venv.

## populate_db.py

Use `python populate_db.py` to create an SQLite database, in the current working directory, containing some juicy image metadata from the Perseverance raw images RSS feed.  If the database already exists, this script will update it with the latest info from the feed.

## combine_images.py

Use `python combine_images.py -r *red_img* -g *green_img* -b *blue_img* *result_img*` to combine color-separation images into a full-color image.  If you omit one or more of the color components, the script will provide a blank (all zero) color-separation for you.

I doubt I can enumerate all of the assumptions and bugs in this code...

## get_rgb_images.py

After you've used `populate_db.py` to create a database, `python get_rgb_images` will download all images listed in the database whose camera filter appears to be an RGB filter.

The script downloads the images to the `image_cache` directory in the current working directory.

## auto_create_rgbs.py

I think this script is the most fun.  It tries to synthesize RGB color images from the right NAVCAM, from all relevant images in the database.  It uses the image_id to guess which color component (red, green, or blue) a given raw image contains.  Then, for every red raw image, it uses the [imagehash](https://pypi.org/project/ImageHash/) package to find the most similar green and blue images; and it combines them.

The script lacks any kind of similarity thresholding.  It will blindly use the most similar green and blue images for a given red image, even if those most similar images are completely unrelated.

The script should crash if there are no green or blue images.  Again, I can't count the number of bugs.

Like `get_rgb_images.py`, this script caches downloaded images in `image_cache`.  But it spews all generated images into the current working directory.