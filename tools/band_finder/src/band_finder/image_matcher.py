#!/usr/bin/env python3
"""
image_matcher adjusts image contrast based on two image samples.
Copyright 2021, Mitch Chapman  All rights reserved
"""

import numpy as np


class ChannelAdjuster:
    def __init__(self, src_sample, target_sample, channel):
        src = src_sample.astype(np.float64)
        targ = target_sample.astype(np.float64)

        src_values = src[:, :, channel].flatten()
        targ_values = targ[:, :, channel].flatten()

        samples = dict()
        for s, t in zip(src_values, targ_values):
            samples.setdefault(s, []).append(t)

        value_map = dict()
        for s, tvals in samples.items():
            value_map[s] = np.mean(tvals)

        ordered_src = sorted(value_map.keys())
        ordered_targ = [value_map[src] for src in ordered_src]

        self._osrc = ordered_src
        self._otarg = ordered_targ
        self._channel = channel

    def adjust(self, image_data):
        values = image_data[:, :, self._channel]
        image_data[:, :, self._channel] = np.interp(
            values, self._osrc, self._otarg
        )


class ImageMatcher:
    """
    ImageMatcher tries to make a source image match
    the appearance of a target image.

    It uses samples of the source and target image, that presumably depict the
    same scene, to characterize the mapping from source to target.
    It does this poorly, by considering image color components separately.
    """

    def __init__(self, src_sample, target_sample):
        """Create an instance.
        src_sample and target_sample are numpy image_data.
        Both show the same scene, but with potentially different colors -
        intensity, saturation, etc.

        Args:
            src_sample (array): A numpy image
            target_sample (array): A numpy image, depicting
                                   the same scene as src_sample but with
                                   possibly different color ranges
        """
        src = src_sample.astype(np.float64)
        targ = target_sample.astype(np.float64)

        self._adjusters = [
            ChannelAdjuster(src, targ, channel) for channel in [0, 1, 2]
        ]

    def adjusted(self, src_image):
        """Get a copy of a source image, adjusted to
        match self's target_sample.

        Note: the result's value data may not be bounded to, e.g., 0..255.0

        Args:
            image (array): numpy image array

        Returns:
            array: the adjusted image array
        """
        result = src_image.copy()
        for adjuster in self._adjusters:
            adjuster.adjust(result)
        return result
