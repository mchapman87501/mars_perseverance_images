import pytest

from pathlib import Path

import cv2
from PIL import Image
import numpy as np
from skimage import io, color
from skimage.util import img_as_uint, img_as_ubyte

from band_finder.bayer_to_rgb import bayer_to_rgb
from band_finder.image_matcher import ImageMatcher


def test_const_diff():
    full_grad = Image.linear_gradient("L").convert("RGB")
    new_size = (4, 32)
    grad = full_grad.resize(new_size)

    solid = Image.new("RGB", grad.size, color="blue")

    src_rgb = Image.blend(grad, solid, 0.5)
    src_data = color.rgb2lab(np.array(src_rgb))

    targ_rgb = Image.blend(grad, solid, 0.2)
    targ_data = color.rgb2lab(np.array(targ_rgb))

    # Matches only value range changes...
    matcher = ImageMatcher(src_data, targ_data)

    # Need to normalize the result data.
    result_data = matcher.adjusted(src_data)

    print("Source:", src_data)
    print("Target:", targ_data)
    print("Result:", result_data)

    def flatcomp(npa, dim=2):
        # All columns should have the same value - gradient.
        dim_vals = npa[:, 0, dim]
        result = dim_vals.tolist()
        return result

    print("Source values:", sorted(set(flatcomp(src_data))))
    print("Target values:", sorted(set(flatcomp(targ_data))))
    print("Result values:", sorted(set(flatcomp(result_data))))

    # Verify the resulting L values are acceptably close to the target.
    v_diff = result_data[:, 0, 0] - targ_data[:, 0, 0]
    print("Target data:", targ_data[:, 0, 0])
    print("Result data:", result_data[:, 0, 0])
    print("Diffs:", v_diff)
    mean_diff = np.abs(np.mean(v_diff))
    assert mean_diff <= 1


def _demosaiced(pathname):
    return bayer_to_rgb(io.imread(pathname))


def _show(image_data):
    # Use PIL to display images because skimage.io.imshow always
    # gives me this error:
    # AttributeError: 'NoneType' object has no attribute
    # 'get_topmost_subplotspec'
    Image.fromarray(image_data).show()


@pytest.mark.parametrize("tile_set", [0, 1])
def test_sample_images_interactive(tile_set):
    # This is an interactive test -- a human needs to visually inspect
    # the results.  Is there any sort of pytest annotation for such tests?
    here = Path(__file__).resolve().parent
    data_dir = here / "data" / "tiles" / str(tile_set)

    left_image = _demosaiced(data_dir / "left_tile.png")
    _show(left_image)

    right_image = _demosaiced(data_dir / "right_tile.png")
    _show(right_image)

    # Left and right should overlap by at least 16 columns.
    h, w = left_image.shape[:2]
    left_crop = left_image[:, w - 16 :, :]

    h, w = right_image.shape[:2]
    right_crop = right_image[:, :16, :]

    left_data = color.rgb2lab(left_crop)
    right_data = color.rgb2lab(right_crop)

    matcher = ImageMatcher(right_data, left_data)

    full_right_data = color.rgb2lab(right_image)
    result_data = img_as_ubyte(
        color.lab2rgb(matcher.adjusted(full_right_data))
    )

    _show(left_crop)
    _show(right_crop)
    _show(result_data)
