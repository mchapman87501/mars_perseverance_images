#!/usr/bin/env python3
"""
tile_brightness_matcher minimizes variations in brightness among image tiles.
"""
# ^^^ /minimizes/tries to minimize/  :)

import numpy as np

from PIL import Image

from .tile_image_grid import TileImageGrid, Edge


class TileBrightnessMatcher:
    """
    TileBrightnessMatcher minimizes variations in brightness among image tiles.
    """

    def __init__(self):
        self._tiles_by_origin = {}  # {(left, top): tile}

    def add(self, tile_image, origin):
        """Add a tile image.

        Args:
            tile_image: a single tile from a larger image
            origin: (x, y) coordinate of the tile's top-left corner

        Raises:
            ValueError: if a tile has already been added for the given origin
        """
        if origin in self._tiles_by_origin:
            raise ValueError(f"Duplicate tile origin {origin}")
        self._tiles_by_origin[origin] = np.array(tile_image)

    def composite(self):
        """Get a consistent-brightness composite image from self's tiles.

        Returns:
            (Image): The composite image.
        """
        grid = TileImageGrid(self._tiles_by_origin)

        # Strategy: march across the tiles, adjusting each to match
        # its "predecessors".  Apply adjustments, then renormalize the
        # component brightnesses across the whole image.
        self._calc_adjustments(grid)
        image_data = self._composite_tiles(grid)
        image_data = self._normalize_values(image_data)
        return Image.fromarray(image_data)

    def _calc_adjustments(self, grid):
        adjustments = np.ones_like(grid.as_array())

        h, w = grid.shape()
        for ygrid in range(h):
            for xgrid in range(w):
                self._adjust_tile(grid, xgrid, ygrid)

    def _adjust_tile(self, grid, xgrid, ygrid):
        # Adjust the values of a tile, in situ.
        edge_ratios = []
        if xgrid > 0:
            neighbor_edge = grid.edge(xgrid - 1, ygrid, Edge.RIGHT)
            edge = grid.edge(xgrid, ygrid, Edge.LEFT)
            if (edge is not None) and (neighbor_edge is not None):
                edge_ratios += self._edge_ratios(edge, neighbor_edge)
        if ygrid > 0:
            neighbor_edge = grid.edge(xgrid, ygrid - 1, Edge.BOTTOM)
            edge = grid.edge(xgrid, ygrid, Edge.TOP)
            if (edge is not None) and (neighbor_edge is not None):
                edge_ratios += self._edge_ratios(edge, neighbor_edge)

        adjustment = np.mean(edge_ratios) if edge_ratios else 1.0
        grid.multiply(xgrid, ygrid, adjustment)

    def _edge_ratios(self, edge0, edge1):
        with np.errstate(divide="ignore", invalid="ignore"):
            ratios = edge1 / edge0
            non_nan = ratios[np.logical_not(np.isnan(ratios))]
            result = non_nan[np.logical_not(np.isinf(non_nan))]
            return result.tolist()

    def _composite_tiles(self, grid):
        width = height = 0
        pixel_shape = None
        records = []

        hgrid, wgrid = grid.shape()
        for ygrid in range(hgrid):
            for xgrid in range(wgrid):
                if grid.tile_is_missing(xgrid, ygrid):
                    continue
                rec = (tile, (x, y, w, h)) = grid.tile_with_origin(
                    xgrid, ygrid)
                records.append(rec)
                tile_x_max = x + w
                tile_y_max = y + h
                width = max(width, tile_x_max)
                height = max(height, tile_y_max)
                pixel_shape = tile.shape[-1]
        result = np.zeros((height, width, pixel_shape), dtype=np.float64)
        for tile, rect in records:
            x, y, w, h = rect
            result[y:y+h, x:x+w] = tile
        return result

    def _normalize_values(self, image_data):
        vmax = np.max(image_data)
        vmin = np.min(image_data)
        dv = vmax - vmin

        max8bit = 255.0

        image_data = (image_data - vmin) / dv * max8bit
        return image_data.astype(np.uint8)
