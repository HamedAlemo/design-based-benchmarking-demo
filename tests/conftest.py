"""Shared fixtures: a tiny synthetic extent on the real grid CRS, used to test M2 and M4 end to end.

The synthetic rasters are software-test data only. They never feed results.
"""

from __future__ import annotations

import shutil

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from shapely.geometry import box

from bowpilot.config import load_config
from bowpilot.grid import Grid


def _write(path, grid, arr, dtype="uint8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **grid.profile(dtype)) as dst:
        dst.write(arr.astype(dtype), 1)


@pytest.fixture(scope="session")
def tiny_cfg(tmp_path_factory):
    """Config rooted in a temp dir with a 1088 x 1280-cell synthetic extent, three model maps and a CVPR file."""
    root = tmp_path_factory.mktemp("tiny")
    cfg = load_config("dev", root=root)
    rng = np.random.default_rng(3)
    grid = Grid("EPSG:5070", 1_700_480.0, 1_980_160.0, 10.0, 1280, 1088)
    grid.to_json(cfg.interim_dir / "grid.json")
    h, w = grid.shape
    state = np.zeros((h, w), dtype=np.uint8)
    state[10:1078, 10:800] = 1
    state[10:1078, 800:1270] = 2
    valid = np.full((h, w), 100, dtype=np.uint8)
    valid[300:310, 100:400] = 60                        # incomplete reference strip, excluded from U
    ref = rng.choice([1, 2, 3, 4, 5], size=(h, w), p=[0.05, 0.35, 0.45, 0.03, 0.12]).astype(np.uint8)
    purity = rng.integers(40, 101, size=(h, w)).astype(np.uint8)
    rd = cfg.rasters_dir
    _write(rd / "state.tif", grid, state)
    _write(rd / "ref_valid.tif", grid, valid)
    _write(rd / "ref_class.tif", grid, np.where(valid == 100, ref, 0))
    _write(rd / "ref_purity.tif", grid, purity)
    for c in range(1, 6):
        _write(rd / f"ref_frac_{c}.tif", grid, np.where(ref == c, purity, (100 - purity) // 4))
    eco = np.where(np.arange(w)[None, :] < 300, 63, 64).repeat(h, axis=0)
    eco[:, 1100:] = 65
    _write(rd / "eco_l3.tif", grid, eco, "uint16")
    for key, err in zip(cfg.model_keys, (0.15, 0.2, 0.25), strict=True):
        wrong = rng.random((h, w)) < err
        alt = rng.integers(0, 6, size=(h, w))
        _write(rd / f"map_{key}.tif", grid, np.where(wrong, alt, ref))
    # a fake CVPR tile: the quarter-quad containing the grid centre, slightly shrunk
    from bowpilot.population.frames import qq_polygon

    cx, cy = grid.x0 + w * 5, grid.y0 - h * 5
    lon, lat = gpd.GeoSeries(gpd.points_from_xy([cx], [cy]), crs=grid.crs).to_crs("EPSG:4269").iloc[0].coords[0]
    step = 0.0625
    qq = gpd.GeoSeries([qq_polygon(int(np.floor(lon / step)), int(np.floor(lat / step)), step)], crs="EPSG:4269")
    shrunk = qq.to_crs(grid.crs).buffer(-50)
    far = gpd.GeoSeries([box(0, 0, 1000, 1000)], crs=grid.crs)  # unmatched tile
    cv = gpd.GeoDataFrame({"name": ["m_test_ne", "m_far_nw"], "prefix": ["md_1m_2013"] * 2, "state": ["MD"] * 2,
                           "split": ["test", "train"]}, geometry=list(shrunk) + list(far), crs=grid.crs)
    cv.to_file(cfg.interim_dir / "cvpr_tiles.gpkg", driver="GPKG")
    yield cfg
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture(scope="session")
def tiny_population(tiny_cfg):
    from bowpilot.population.pipeline import run_population

    return tiny_cfg, run_population(tiny_cfg)
