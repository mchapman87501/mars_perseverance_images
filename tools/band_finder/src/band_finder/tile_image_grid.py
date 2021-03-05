#!/usr/bin/env python3
"""
tile_image_grid manages a grid of image tiles.
"""

from enum import Enum

import numpy as np


class Edge(Enum):
    LEFT = "left"
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"


class TileImageGrid:
    def __init__(self, tiles_by_origin):
        origins = np.array(list(tiles_by_origin.keys()))
        self._xvals = list(sorted(set(origins[:, 0])))
        self._yvals = list(sorted(set(origins[:, 1])))
        w = len(self._xvals)
        h = len(self._yvals)

        # PIL & numpy represent image data as rows x cols x components.
        # Try to be consistent here.
        grid = self._grid = np.empty((h, w), dtype=object)
        for iy, yval in enumerate(self._yvals):
            for ix, xval in enumerate(self._xvals):
                grid[iy, ix] = tiles_by_origin.get((xval, yval))

    def as_array(self):
        return self._grid

    def shape(self):
        return self._grid.shape

    def tile_is_missing(self, xgrid, ygrid):
        return self._grid[ygrid, xgrid] is None

    def edge(self, xgrid, ygrid, edge):
        # Get the portion of the tile that overlaps the adjacent
        # tile on the specified edge.
        tile = self._grid[ygrid, xgrid]
        # Tiles may be missing:
        if tile is None:
            return None

        try:
            name = f"_edge_{edge.value}".lower()
            method = getattr(self, name)
            return method(xgrid, ygrid)
        except Exception:
            raise IndexError(f"Invalid edge {(xgrid, ygrid, edge)}")

    def _edge_left(self, xgrid, ygrid):
        tile = self._grid[ygrid, xgrid]
        # Tiles may be missing.
        if tile is None:
            return None

        if xgrid <= 0:
            # All rows, first column -- nothing to overlap.
            return tile[:, :1]

        # By how much do I overlap my left neighbor?
        neighbor = self._grid[ygrid, xgrid - 1]
        if neighbor is None:
            return None

        x_left = self._xvals[xgrid - 1]
        w_left = neighbor.shape[1]  # numpy images: (h, w)

        x = self._xvals[xgrid]
        overlap = (x_left + w_left) - x
        # Return all rows, overlap columns each.
        return tile[:, :overlap]

    def _edge_right(self, xgrid, ygrid):
        tile = self._grid[ygrid, xgrid]
        if xgrid >= len(self._xvals) - 1:
            # All rows, last column -- nothing to overlap
            return tile[:, -1:]

        x_right = self._xvals[xgrid + 1]
        x = self._xvals[xgrid]
        # Return all rows, overlap columns each
        return tile[:, (x_right - x):]

    def _edge_top(self, xgrid, ygrid):
        tile = self._grid[ygrid, xgrid]
        if tile is None:
            return None

        if ygrid <= 0:
            # first row, all columns - nothing to overlap
            return tile[:1, :]

        # By how much do I overlap my neighbor?
        neighbor = self._grid[ygrid - 1, xgrid]
        if neighbor is None:
            return None

        y_top = self._yvals[ygrid - 1]
        h_top = neighbor.shape[0]

        y = self._yvals[ygrid]
        overlap = (y_top + h_top) - y
        return tile[:overlap, :]

    def _edge_bottom(self, xgrid, ygrid):
        tile = self._grid[ygrid, xgrid]
        if tile is None:
            return None

        if ygrid >= len(self._yvals) - 1:
            return tile[-1:, :]

        # By how much do I overlap my neighbor?
        y = self._yvals[ygrid]
        y_bot = self._yvals[ygrid + 1]
        # Translate neighbor's first row to be an offset from self's
        # first row:
        y_rel = y_bot - y
        return tile[y_rel:, :]

    def multiply(self, xgrid, ygrid, value):
        """Multiply a tile by a scalar value, mutating in situ.

        Args:
            xgrid (int): x index of tile
            ygrid (int): y index of tile
            value (number): The amount by which to multiply values
        """
        tile = self._grid[ygrid, xgrid]
        if tile is not None:
            self._grid[ygrid, xgrid] = tile * value

    def tile_with_origin(self, xgrid, ygrid):
        """Get a tile, with its composite-image coordinates.

        Args:
            xgrid (int): x index of tile
            ygrid (int): y index of tile

        Returns:
            tuple: (image_data, (x, y, w, h)) or None
        """
        tile = self._grid[ygrid, xgrid]
        if tile is None:
            return None

        left = self._xvals[xgrid]
        top = self._yvals[ygrid]
        height, width = tile.shape[:2]
        return (tile, (left, top, width, height))
