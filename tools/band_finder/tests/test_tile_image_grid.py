from band_finder.tile_image_grid import TileImageGrid, Edge
import numpy as np

import pytest


def test_init():
    tbo = {
        (0, 0): "a",
        (1024, 0): "b",
        (2048, 0): "c",
        (0, 960): "d",
        (2048, 960): "e",
    }
    grid = TileImageGrid(tbo)
    assert grid is not None
    assert grid.shape() == (2, 3)

    # Whitebox:
    gg = grid._grid
    assert gg[0, 0] == "a"
    assert gg[0, 1] == "b"
    assert gg[1, 1] is None


def _get_test_grid():
    tbo = {
        (0, 0): np.array(
            [
                [0.0, 0.0, 0.0, 1.0],
                [3.0, 4.0, 4.0, 1.0],
                [3.0, 2.0, 2.0, 2.0],
            ]
        ),
    }
    return TileImageGrid(tbo)


edge_values_test_data = [
    [Edge.TOP, [[0.0, 0.0, 0.0, 1.0]]],
    [Edge.RIGHT, [[1.0], [1.0], [2.0]]],
    [Edge.BOTTOM, [[3.0, 2.0, 2.0, 2.0]]],
    [Edge.LEFT, [[0.0], [3.0], [3.0]]],
]


@pytest.mark.parametrize("edge, expected", edge_values_test_data)
def test_edge_values(edge, expected):
    grid = _get_test_grid()
    actual = grid.edge(0, 0, edge)
    assert actual.tolist() == expected


def test_edge_index_1():
    grid = _get_test_grid()
    with pytest.raises(IndexError):
        grid.edge(1, 0, Edge.TOP)


def test_edge_index_2():
    grid = _get_test_grid()
    with pytest.raises(IndexError):
        grid.edge(0, 0, "invalid enum value")


# Test with greater edge overlaps.
@pytest.fixture
def overlapping_grid():
    wtile = 6
    htile = 4
    xover = 2
    yover = 1

    # If you read a 1296x976 RGB image using PIL, and convert it
    # to a numpy array, its shape will be (976, 1296, 3).  Rows x cols x comps
    tile_shape = (htile, wtile)

    tbo = {}
    x = 0
    for ix in range(3):
        y = 0
        for iy in range(3):
            value = ix * ix + iy * iy
            tbo[(x, y)] = np.full(tile_shape, value)
            print("Tile", (x, y), "=", tile_shape, "x", value)

            y += htile - yover

        x += wtile - xover
    return TileImageGrid(tbo)


overlap_edge_values_test_data = [
    [0, 0, Edge.LEFT, [[0.0]] * 4],
    [0, 0, Edge.TOP, [[0.0] * 6]],
    [1, 1, Edge.RIGHT, [[2.0, 2.0]] * 4],
    [0, 1, Edge.BOTTOM, [[1.0] * 6]],
    [2, 2, Edge.LEFT, [[8.0, 8.0]] * 4],
]


@pytest.mark.parametrize("x, y, edge, expected", overlap_edge_values_test_data)
def test_overlap_edge_values(x, y, edge, expected, overlapping_grid):
    actual = overlapping_grid.edge(x, y, edge)
    assert actual.tolist() == expected
