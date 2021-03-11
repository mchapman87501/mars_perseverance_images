#!/usr/bin/env python3
"""
bayer_to_rgb de-mosaics full sensor readouts to RGB images.
Copyright 2021, Mitch Chapman  All rights reserved
"""

import cv2
from skimage import color
from skimage.util import img_as_uint, img_as_ubyte


def bayer_to_rgb(full_sensor_image):
    """
    Demosaic a full readout of a sensor that has a Bayer-pattern
    filter overlaid on it.
    """

    # Cop out - use someone else's demosaicing algorithms.
    # https://gist.github.com/bbattista/8358ccafecf927ae1c58c944ab470ffb

    bayer = img_as_uint(color.rgb2gray(full_sensor_image))
    demosaic = cv2.cvtColor(bayer, cv2.COLOR_BAYER_BG2RGB)
    return img_as_ubyte(demosaic)
