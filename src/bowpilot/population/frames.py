"""Tile frame, chip frame, rare-class tags, and strata for D, D2 and F (M2 sections 2 to 4).

Writes cell-table columns tile.npy, chip.npy, strat_D.npy, strat_D2.npy, strat_F_<model>.npy and lookup tables in
data/<extent>/interim/frames/.
"""

from __future__ import annotations

import json
import logging

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Polygon

from bowpilot.config import Config
from bowpilot.grid import Grid
from bowpilot.population.cell_table import load, save_column, tile_ixiy

log = logging.getLogger(__name__)
CHUNK = 50_000_000
NO_MAJORITY = 10


def _chunks(n: int):
    for s in range(0, n, CHUNK):
        yield slice(s, min(n, s + CHUNK))


def _chunked_unique(arr: np.ndarray) -> np.ndarray:
    keys = np.unique(np.concatenate([np.unique(arr[sl]) for sl in _chunks(len(arr))]))
    return keys


def _chunked_index(arr: np.ndarray, keys: np.ndarray) -> np.ndarray:
    out = np.empty(len(arr), dtype=np.int32)
    for sl in _chunks(len(arr)):
        out[sl] = np.searchsorted(keys, arr[sl])
    return out


def _chunked_bincount(idx_fn, n: int, minlength: int) -> np.ndarray:
    tot = np.zeros(minlength, dtype=np.int64)
    for sl in _chunks(n):
        tot += np.bincount(idx_fn(sl), minlength=minlength)
    return tot


def qq_polygon(ix: int, iy: int, step: float, n: int = 16) -> Polygon:
    """Quarter-quadrangle polygon in lon/lat, densified so the projected edges follow the true lines."""
    x0, y0 = ix * step, iy * step
    t = np.linspace(0, 1, n + 1)
    xs = np.concatenate([x0 + t * step, np.full(n, x0 + step), x0 + step - t[1:] * step, np.full(n, x0)])
    ys = np.concatenate([np.full(n + 1, y0), y0 + t[1:] * step, np.full(n, y0 + step), y0 + step - t[1:] * step])
    return Polygon(zip(xs, ys, strict=True))


# ------------------------------------------------------------------------------------------------ tiles
def build_tiles(cfg: Config) -> dict:
    tk = load(cfg, "tile_key")
    state = load(cfg, "state")
    n = len(tk)
    keys = _chunked_unique(tk)
    tile = _chunked_index(tk, keys)
    save_column(cfg, "tile", tile)
    m = len(keys)
    counts = _chunked_bincount(lambda sl: tile[sl].astype(np.int64) * 2 + (state[sl].astype(np.int64) - 1), n, 2 * m)
    counts = counts.reshape(m, 2)
    codes = [s["code"] for s in cfg.states]
    stratum = np.array(codes)[counts.argmax(axis=1)]   # ties go to the lower code (MD)
    ix, iy = tile_ixiy(keys)
    step = float(cfg.frames["tiles"]["quarter_quad_grid"]["step_deg"])
    meta = pd.DataFrame({"tile_id": np.arange(m), "ix": ix, "iy": iy, "stratum": stratum,
                         "n_cells": counts.sum(axis=1), "n_md": counts[:, 0], "n_de": counts[:, 1]})
    polys = gpd.GeoDataFrame(meta[["tile_id"]].copy(), geometry=[qq_polygon(a, b, step) for a, b in zip(ix, iy,
                             strict=True)], crs=cfg.frames["tiles"]["quarter_quad_grid"]["grid_crs"]).to_crs(cfg.crs)
    match = match_cvpr(cfg, meta, polys)
    meta = meta.merge(match[["tile_id", "cvpr_name", "cvpr_split", "cvpr_iou"]], on="tile_id", how="left")
    fdir = cfg.interim_dir / "frames"
    fdir.mkdir(parents=True, exist_ok=True)
    meta.to_parquet(fdir / "tiles_frame.parquet")
    polys.to_file(fdir / "tiles.gpkg", driver="GPKG")
    abbr = {s["code"]: s["abbr"] for s in cfg.states}
    return {"M_tiles": m, "M_by_state": {abbr[c]: int((stratum == c).sum()) for c in codes},
            "cells_per_tile": meta["n_cells"].describe().round(1).to_dict(),
            "sum_n_cells": int(meta["n_cells"].sum()), "N": n,
            "cvpr": cvpr_summary(match)}


def match_cvpr(cfg: Config, meta: pd.DataFrame, polys: gpd.GeoDataFrame) -> pd.DataFrame:
    """Match each MD/DE CVPR tile to the frame tile containing its centroid; IoU computed in the grid CRS."""
    path = cfg.interim_dir / "cvpr_tiles.gpkg"
    cv = gpd.read_file(path).to_crs(cfg.crs)
    step = float(cfg.frames["tiles"]["quarter_quad_grid"]["step_deg"])
    cent = cv.geometry.centroid.to_crs(cfg.frames["tiles"]["quarter_quad_grid"]["grid_crs"])
    cix, ciy = np.floor(cent.x / step).astype(int), np.floor(cent.y / step).astype(int)
    lookup = {(int(a), int(b)): int(t) for a, b, t in zip(meta["ix"], meta["iy"], meta["tile_id"], strict=True)}
    poly_by_id = dict(zip(polys["tile_id"], polys.geometry, strict=True))
    rows = []
    for i, r in enumerate(cv.itertuples()):
        tid = lookup.get((int(cix.iloc[i]), int(ciy.iloc[i])))
        iou = np.nan
        if tid is not None:
            fp = poly_by_id[tid]
            iou = fp.intersection(r.geometry).area / fp.union(r.geometry).area
        rows.append({"cvpr_name": r.name, "cvpr_state": r.state, "cvpr_split": r.split, "tile_id": tid,
                     "cvpr_iou": iou})
    df = pd.DataFrame(rows)
    (cfg.interim_dir / "frames").mkdir(parents=True, exist_ok=True)
    df.to_csv(cfg.interim_dir / "frames" / "cvpr_match.csv", index=False)
    ok = df[df["cvpr_iou"] >= float(cfg.frames["tiles"]["quarter_quad_grid"]["match_min_iou"])]
    return ok.drop_duplicates("tile_id")


def cvpr_summary(match_ok: pd.DataFrame) -> dict:
    return {"matched": int(len(match_ok)),
            "matched_by_state_split": {f"{a}_{b}": int(v) for (a, b), v in
                                       match_ok.groupby(["cvpr_state", "cvpr_split"]).size().items()},
            "iou_min": float(match_ok["cvpr_iou"].min()) if len(match_ok) else None,
            "iou_median": float(match_ok["cvpr_iou"].median()) if len(match_ok) else None}


# ------------------------------------------------------------------------------------------------ chips
def build_chips(cfg: Config, grid: Grid) -> dict:
    size = cfg.chip_size
    row, col, ref = load(cfg, "row"), load(cfg, "col"), load(cfg, "ref")
    n = len(row)
    ncc = (grid.width + size - 1) // size
    key = np.empty(n, dtype=np.int64)
    for sl in _chunks(n):
        key[sl] = (row[sl].astype(np.int64) // size) * ncc + col[sl] // size
    keys = _chunked_unique(key)
    chip = _chunked_index(key, keys)
    del key
    save_column(cfg, "chip", chip)
    m = len(keys)
    cls_counts = _chunked_bincount(lambda sl: chip[sl].astype(np.int64) * 5 + (ref[sl].astype(np.int64) - 1),
                                   n, 5 * m).reshape(m, 5)
    pop_props = cls_counts.sum(axis=0) / n
    rarity = [int(c) for c in np.argsort(pop_props, kind="stable") + 1]          # rarest first
    n_cells = cls_counts.sum(axis=1)
    share = cls_counts / n_cells[:, None]
    thr = float(cfg.frames["chips"]["rare_tag_min_fraction"])
    tag = np.zeros(m, dtype=np.int8)
    for c in reversed(rarity):            # assign from most common to rarest; the rarest qualifying class wins
        tag[share[:, c - 1] >= thr] = c
    meta = pd.DataFrame({"chip_id": np.arange(m), "chip_row": keys // ncc, "chip_col": keys % ncc,
                         "n_cells": n_cells, "complete": n_cells == size * size, "tag": tag})
    fdir = cfg.interim_dir / "frames"
    fdir.mkdir(parents=True, exist_ok=True)
    meta.to_parquet(fdir / "chips_frame.parquet")
    (fdir / "rarity.json").write_text(json.dumps({"rarity_order": rarity,
                                                  "population_props": pop_props.round(6).tolist()}))
    per_tag = {"complete": meta[meta.complete].groupby("tag").size().astype(int).to_dict(),
               "all": meta.groupby("tag").size().astype(int).to_dict()}
    return {"M_chips": m, "complete_chips": int(meta["complete"].sum()), "sum_n_cells": int(n_cells.sum()),
            "rarity_order": rarity, "pop_props": pop_props.round(6).tolist(), "chips_per_tag": per_tag}


# ------------------------------------------------------------------------------------------------ strata
def strata_D(cfg: Config) -> dict:  # noqa: N802
    """Consensus class x agreement level (ids (c - 1) * 2 + {0: 3 of 3, 1: 2 of 3}); 10 = no majority."""
    maps = [load(cfg, f"map_{k}") for k in cfg.model_keys]
    n = len(maps[0])
    out = np.empty(n, dtype=np.uint8)
    for sl in _chunks(n):
        m = np.stack([a[sl] for a in maps], axis=1)
        votes = np.stack([(m == c).sum(axis=1) for c in range(1, 6)], axis=1)   # (n, 5)
        best = votes.argmax(axis=1)
        nb = votes.max(axis=1)
        sid = np.where(nb >= 2, best * 2 + np.where(nb == len(maps), 0, 1), NO_MAJORITY)
        out[sl] = sid.astype(np.uint8)
    save_column(cfg, "strat_D", out)
    nh = _chunked_bincount(lambda sl: out[sl].astype(np.int64), n, 11)
    look = pd.DataFrame({"stratum_id": np.arange(11), "consensus_class": [i // 2 + 1 for i in range(10)] + [0],
                         "level": ["agree3", "agree2"] * 5 + ["no_majority"], "N_h": nh})
    look = look[look.N_h > 0]
    look.to_csv(cfg.interim_dir / "frames" / "strata_D.csv", index=False)
    return {"H": int(len(look)), "sum_N_h": int(look.N_h.sum()), "table": look.to_dict("records")}


def strata_D2(cfg: Config) -> dict:  # noqa: N802
    """State x EPA L3 ecoregion; strata below the configured fraction of N merge into "<state>_other"."""
    state, eco = load(cfg, "state"), load(cfg, "eco")
    n = len(state)
    combo = _chunked_bincount(lambda sl: state[sl].astype(np.int64) * 1000 + eco[sl], n, 3000)
    frac = float(cfg.arms["D2"]["merge_small_strata_below_fraction"])
    abbr = {s["code"]: s["abbr"] for s in cfg.states}
    lut = np.full(3000, -1, dtype=np.int32)
    rows, next_id = [], 0
    for code in sorted(abbr):
        keys = [k for k in range(code * 1000, code * 1000 + 1000) if combo[k] > 0]
        small = [k for k in keys if combo[k] < frac * n]
        for k in keys:
            if k not in small:
                lut[k] = next_id
                rows.append({"stratum_id": next_id, "state": abbr[code], "eco_l3": k % 1000, "name":
                             f"{abbr[code]}_{k % 1000}", "N_h": int(combo[k])})
                next_id += 1
        if small:
            for k in small:
                lut[k] = next_id
            rows.append({"stratum_id": next_id, "state": abbr[code], "eco_l3": -1, "name": f"{abbr[code]}_other",
                         "N_h": int(sum(combo[k] for k in small)), "merged_eco": [k % 1000 for k in small]})
            next_id += 1
    out = np.empty(n, dtype=np.uint16)
    for sl in _chunks(n):
        out[sl] = lut[state[sl].astype(np.int64) * 1000 + eco[sl]]
    save_column(cfg, "strat_D2", out)
    look = pd.DataFrame(rows)
    look.to_csv(cfg.interim_dir / "frames" / "strata_D2.csv", index=False)
    return {"H": int(len(look)), "sum_N_h": int(look.N_h.sum()), "table": look.drop(columns=["merged_eco"],
                                                                                         errors="ignore")
            .to_dict("records"), "merged": {r["name"]: r.get("merged_eco") for r in rows if "merged_eco" in r}}


def strata_F(cfg: Config) -> dict:  # noqa: N802
    """For each model, stratum = its own map class 0..5 (empty classes dropped)."""
    res = {}
    for k in cfg.model_keys:
        m = load(cfg, f"map_{k}")
        save_column(cfg, f"strat_F_{k}", np.asarray(m, dtype=np.uint8))
        nh = _chunked_bincount(lambda sl, m=m: m[sl].astype(np.int64), len(m), 6)
        look = pd.DataFrame({"stratum_id": np.arange(6), "N_h": nh})
        look = look[look.N_h > 0]
        look.to_csv(cfg.interim_dir / "frames" / f"strata_F_{k}.csv", index=False)
        res[k] = {"H": int(len(look)), "sum_N_h": int(look.N_h.sum()), "N_h": dict(zip(look.stratum_id.astype(int),
                                                                                        look.N_h.astype(int),
                                                                                        strict=True))}
    return res
