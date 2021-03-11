#!/usr/bin/env python3
"""
tile_matcher minimizes variations in brightness among image tiles.
Copyright 2021, Mitch Chapman  All rights reserved
"""
# ^^^ /minimizes/tries to minimize/  :)

import logging

import numpy as np

from .tile_image_grid import TileImageGrid, Edge
from .image_matcher import ImageMatcher


def logger():
    return logging.getLogger(__name__)


class TileMatcher:
    """
    TileMatcher minimizes variations in brightness among image tiles.
    """

    def __init__(self, name="unnamed"):
        self._name = name
        self._tiles_by_origin = {}  # {(left, top): tile}
        self._diag_plot = None

    def add(self, tile_image, origin):
        """Add a tile image.

        Args:
            tile_image (Image.Image): a single tile image from a larger image
            origin: (x, y) coordinate of the tile's top-left corner

        Raises:
            ValueError: if a tile has already been added for the given origin
        """
        if origin in self._tiles_by_origin:
            raise ValueError(f"Duplicate tile origin {origin}")

        logger().debug(
            f"Adding shape {tile_image.shape}, type {tile_image.dtype}"
        )

        self._tiles_by_origin[origin] = tile_image

    def composite(self):
        """Get a consistent-brightness composite image from self's tiles.

        Returns:
            array: The composite image array -- note that the representation
                   is not guaranteed.
        """

        grid = TileImageGrid(self._tiles_by_origin)
        rows, cols = grid.shape()
        logger().debug(f"Created grid with shape {grid.shape()}")

        # self._diag_plot = DiagPlotter(self._name, rows, cols)

        # Strategy: march across the tiles, adjusting each to match
        # its "predecessors".  Apply adjustments, then renormalize the
        # component brightnesses across the whole image.
        self._match_all_tiles(grid)
        image_data = self._composited_tiles(grid)

        # self._diag_plot.finish()

        return image_data

    def _match_all_tiles(self, grid):
        h, w = grid.shape()
        for ygrid in range(h):
            for xgrid in range(w):
                self._match_tile_to_predecessors(grid, xgrid, ygrid)

    def _match_tile_to_predecessors(self, grid, xgrid, ygrid):
        # Match the brightness of a tile to all adjacent tiles above or to
        # its left.
        # Changes tile data in situ.

        if (xgrid, ygrid) == (0, 0):
            # This is the ur-tile.
            return

        if grid.tile_is_missing(xgrid, ygrid):
            # This tile is missing...
            return

        # If this tile is in column 0, match it to the tile above.
        # Otherwise match to the tile to the left.
        # In every case, assume the target tile has already been adjusted.
        target_edge = None
        edge = None

        adjusted_images = []

        if xgrid > 0:
            target_edge = grid.edge(xgrid - 1, ygrid, Edge.RIGHT)
            edge = grid.edge(xgrid, ygrid, Edge.LEFT)
            adjusted = self._match_along(grid, xgrid, ygrid, edge, target_edge)
            if adjusted is not None:
                adjusted_images.append(adjusted)

        elif ygrid > 0:
            target_edge = grid.edge(xgrid, ygrid - 1, Edge.BOTTOM)
            edge = grid.edge(xgrid, ygrid, Edge.TOP)
            adjusted = self._match_along(grid, xgrid, ygrid, edge, target_edge)
            if adjusted is not None:
                adjusted_images.append(adjusted)

        if adjusted_images:
            summed = adjusted_images[0].astype(np.float64)
            for ai in adjusted_images[1:]:
                summed += ai.astype(np.float64)
            averaged = summed / len(adjusted_images)
            grid.set_tile(xgrid, ygrid, averaged)

    def _match_along(self, grid, xgrid, ygrid, edge, target_edge):
        # Tiles, therefore edges, may be missing.
        if (edge is not None) and (target_edge is not None):
            # This may overwrite an existing subplot...
            curr_tile = grid.tile(xgrid, ygrid)
            # self._diag_plot.plot(xgrid, ygrid, curr_tile, edge, target_edge)
            matcher = ImageMatcher(edge, target_edge)
            return matcher.adjusted(curr_tile)

    def _composited_tiles(self, grid):
        logger = logging.getLogger(__name__)

        width = height = 0
        pixel_shape = None
        records = []

        hgrid, wgrid = grid.shape()

        for ygrid in range(hgrid):
            for xgrid in range(wgrid):
                rec = grid.tile_with_origin(xgrid, ygrid)
                if rec is not None:
                    records.append(rec)
                    (tile, (x, y, w, h)) = rec
                    tile_x_max = x + w
                    tile_y_max = y + h
                    width = max(width, tile_x_max)
                    height = max(height, tile_y_max)
                    pixel_shape = tile.shape[-1]
                else:
                    logger.warning(f"Blank tile at {(xgrid, ygrid)}")

        result_shape = (height, width, pixel_shape)
        logger.debug(f"Result shape: {result_shape}")
        result = np.zeros(result_shape, dtype=np.float32)
        for tile, rect in records:
            x, y, w, h = rect
            result[y:y + h, x:x + w] = tile
        return result
