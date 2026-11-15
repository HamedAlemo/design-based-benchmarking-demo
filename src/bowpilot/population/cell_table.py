"""Population mask and per-column memmaps of the cell table (M2 section 1).

Population U: cells with state > 0 and ref_valid == 100. Cell order is row-major over the grid. Every column is a
.npy file of length N in data/<extent>/interim/cells/. Built from full-width row strips, so no full-extent raster is
held in memory.

Tile membership (M2 section 2) is computed per cell from the NAD83 (EPSG:4269) longitude and latitude of the cell
centre: tile key (ix, iy) = (floor(lon / step), floor(lat / step)). This is exactly "the quarter-quadrangle polygon
that contains the centre", since quarter-quadrangle edges are lines of constant longitude or latitude in NAD83.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import rasterio
from numpy.lib.format import open_memmap
from pyproj import Transformer
from rasterio.windows import Window

from bowpilot.config import Config
from bowpilot.grid import Grid

log = logging.getLogger(__name__)
STRIP_ROWS = 256
TILE_KEY_OFFSET = 1 << 20   # tile key = (ix + OFF) * 2^21 + (iy + OFF), keeps keys positive


def tile_key(ix: np.ndarray, iy: np.ndarray) -> np.ndarray:
    return (ix.astype(np.int64) + TILE_KEY_OFFSET) * (1 << 21) + (iy.astype(np.int64) + TILE_KEY_OFFSET)


def tile_ixiy(key: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    key = np.asarray(key, dtype=np.int64)
    return key // (1 << 21) - TILE_KEY_OFFSET, key % (1 << 21) - TILE_KEY_OFFSET


def raster_columns(cfg: Config) -> dict[str, tuple[Path, str]]:
    rd = cfg.rasters_dir
    cols = {"ref": (rd / "ref_class.tif", "uint8"), "purity": (rd / "ref_purity.tif", "uint8"),
            "state": (rd / "state.tif", "uint8"), "eco": (rd / "eco_l3.tif", "uint16")}
    cols |= {f"frac_{c}": (rd / f"ref_frac_{c}.tif", "uint8") for c in range(1, 6)}
    cols |= {f"map_{k}": (rd / f"map_{k}.tif", "uint8") for k in cfg.model_keys}
    return cols


def strips(grid: Grid):
    for r in range(0, grid.height, STRIP_ROWS):
        yield Window(0, r, grid.width, min(STRIP_ROWS, grid.height - r))


def build_cell_table(cfg: Config, grid: Grid) -> dict:
    """Write row, col, raster columns, tile_key and chip_key memmaps. Returns counts for the report."""
    out = cfg.cells_dir
    out.mkdir(parents=True, exist_ok=True)
    rd = cfg.rasters_dir
    # pass 1: N and exclusions
    n_total, excl = 0, {s["code"]: 0 for s in cfg.states}
    n_state = {s["code"]: 0 for s in cfg.states}
    with rasterio.open(rd / "state.tif") as st, rasterio.open(rd / "ref_valid.tif") as va:
        for w in strips(grid):
            s = st.read(1, window=w)
            v = va.read(1, window=w)
            for code in n_state:
                n_state[code] += int(((s == code) & (v == 100)).sum())
                excl[code] += int(((s == code) & (v < 100)).sum())
    n_total = sum(n_state.values())
    log.info("N = %d", n_total)
    cols = raster_columns(cfg)
    mm = {name: open_memmap(out / f"{name}.npy", mode="w+", dtype=dt, shape=(n_total,))
          for name, (_, dt) in cols.items()}
    mm["row"] = open_memmap(out / "row.npy", mode="w+", dtype=np.int32, shape=(n_total,))
    mm["col"] = open_memmap(out / "col.npy", mode="w+", dtype=np.int32, shape=(n_total,))
    mm["tile_key"] = open_memmap(out / "tile_key.npy", mode="w+", dtype=np.int64, shape=(n_total,))
    step = float(cfg.frames["tiles"]["quarter_quad_grid"]["step_deg"])
    to_ll = Transformer.from_crs(grid.crs, cfg.frames["tiles"]["quarter_quad_grid"]["grid_crs"], always_xy=True)
    srcs = {name: rasterio.open(p) for name, (p, _) in cols.items()}
    srcs["valid"] = rasterio.open(rd / "ref_valid.tif")
    pos = 0
    try:
        for w in strips(grid):
            s = srcs["state"].read(1, window=w)
            v = srcs["valid"].read(1, window=w)
            pop = (s > 0) & (v == 100)
            n = int(pop.sum())
            if n == 0:
                continue
            rr, cc = np.nonzero(pop)
            rows = rr.astype(np.int32) + int(w.row_off)
            mm["row"][pos:pos + n] = rows
            mm["col"][pos:pos + n] = cc.astype(np.int32)
            for name in cols:
                mm[name][pos:pos + n] = s[pop] if name == "state" else srcs[name].read(1, window=w)[pop]
            x, y = grid.cell_centers(rows, cc)
            lon, lat = to_ll.transform(x, y)
            mm["tile_key"][pos:pos + n] = tile_key(np.floor(np.asarray(lon) / step), np.floor(np.asarray(lat) / step))
            pos += n
    finally:
        for src in srcs.values():
            src.close()
    assert pos == n_total, (pos, n_total)
    for a in mm.values():
        a.flush()
    abbr = {s["code"]: s["abbr"] for s in cfg.states}
    meta = {"N": n_total, "N_by_state": {abbr[c]: n for c, n in n_state.items()},
            "excluded_incomplete_reference_by_state": {abbr[c]: n for c, n in excl.items()}}
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def load(cfg: Config, name: str, mode: str = "r") -> np.ndarray:
    """Open one cell-table column as a read-only memmap."""
    return np.load(cfg.cells_dir / f"{name}.npy", mmap_mode=mode)


def save_column(cfg: Config, name: str, arr: np.ndarray) -> None:
    np.save(cfg.cells_dir / f"{name}.npy", arr)
