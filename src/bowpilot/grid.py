"""Analysis grid: CRS, affine transform, shape; bbox to window; cell index to row/col.

The grid is EPSG:5070 with 10 m cells whose edges sit on multiples of 10 m (config/extent.yaml). It is saved once
per extent in data/<extent>/interim/grid.json and every raster in the pipeline uses exactly this grid.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from affine import Affine
from rasterio.windows import Window


@dataclass(frozen=True)
class Grid:
    """A north-up raster grid.

    x0, y0 : coordinates (m) of the upper-left corner. res : cell size (m). width, height : cells.
    """

    crs: str
    x0: float
    y0: float
    res: float
    width: int
    height: int

    @property
    def transform(self) -> Affine:
        return Affine(self.res, 0.0, self.x0, 0.0, -self.res, self.y0)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """(left, bottom, right, top) in metres."""
        return (self.x0, self.y0 - self.height * self.res, self.x0 + self.width * self.res, self.y0)

    @classmethod
    def from_bounds(cls, crs: str, bounds: tuple[float, float, float, float], res: float, multiple: float) -> Grid:
        """Snap (left, bottom, right, top) outward to multiples of `multiple` metres."""
        left, bottom, right, top = bounds
        left = math.floor(left / multiple) * multiple
        bottom = math.floor(bottom / multiple) * multiple
        right = math.ceil(right / multiple) * multiple
        top = math.ceil(top / multiple) * multiple
        return cls(crs, float(left), float(top), float(res), int(round((right - left) / res)),
                   int(round((top - bottom) / res)))

    def to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        d = {"crs": self.crs, "x0": self.x0, "y0": self.y0, "res": self.res, "width": self.width,
             "height": self.height, "transform": list(self.transform)[:6]}
        path.write_text(json.dumps(d, indent=2))

    @classmethod
    def from_json(cls, path: Path) -> Grid:
        d = json.loads(Path(path).read_text())
        return cls(d["crs"], d["x0"], d["y0"], d["res"], d["width"], d["height"])

    def profile(self, dtype: str = "uint8", nodata: float | None = None) -> dict:
        """A rasterio GTiff profile for this grid (tiled, deflate)."""
        p = {"driver": "GTiff", "crs": self.crs, "transform": self.transform, "width": self.width,
             "height": self.height, "count": 1, "dtype": dtype, "compress": "deflate", "tiled": True,
             "blockxsize": 512, "blockysize": 512, "BIGTIFF": "IF_SAFER"}
        if nodata is not None:
            p["nodata"] = nodata
        return p

    def windows(self, size: int = 512):
        """Yield (row_off, col_off, Window) blocks of at most size x size cells, row-major."""
        for r in range(0, self.height, size):
            for c in range(0, self.width, size):
                yield Window(c, r, min(size, self.width - c), min(size, self.height - r))

    def window_bounds(self, win: Window) -> tuple[float, float, float, float]:
        left = self.x0 + win.col_off * self.res
        top = self.y0 - win.row_off * self.res
        return (left, top - win.height * self.res, left + win.width * self.res, top)

    def cell_centers(self, rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Centre coordinates (m) of cells given int arrays of rows and cols."""
        x = self.x0 + (np.asarray(cols, dtype=np.float64) + 0.5) * self.res
        y = self.y0 - (np.asarray(rows, dtype=np.float64) + 0.5) * self.res
        return x, y

    def index_to_rowcol(self, idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Row-major flat grid index to (row, col)."""
        idx = np.asarray(idx, dtype=np.int64)
        return idx // self.width, idx % self.width

    def rowcol_to_index(self, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
        return np.asarray(rows, dtype=np.int64) * self.width + np.asarray(cols, dtype=np.int64)
