"""Per-PSU confusion and discordant arrays for tiles and chips (M2 section 5).

Files in data/<extent>/interim/units/ (K models, P = K (K - 1) / 2 pairs in order (0,1), (0,2), (1,2)):
  tiles_conf.npy  (M_tiles, K, 6, 5) int64    counts of (map class, ref class) over population cells in the tile
  tiles_disc.npy  (M_tiles, P, 2) int64       McNemar counts: [k right & l wrong, l right & k wrong]
  tiles_meta.parquet                          tile id, stratum, n_cells, CVPR name / split if matched
  chips_conf.npy  (M_chips, T, K, 6, 5) int64 per purity threshold tau (scored = purity >= round(100 tau))
  chips_disc.npy  (M_chips, T, P, 2) int64
  chips_meta.parquet                          chip id, tag, complete, n_cells, n_scored_<tau>
All computed with chunked np.bincount on a combined index, never a Python loop over cells.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from bowpilot.config import Config
from bowpilot.population.cell_table import load

log = logging.getLogger(__name__)
CHUNK = 20_000_000


def purity_min_counts(cfg: Config) -> list[int]:
    """Purity thresholds as minimum plurality counts out of 100 pixels."""
    return [int(round(100 * t)) for t in cfg.purity_thresholds]


def unit_arrays(cfg: Config, unit: np.ndarray, n_units: int, mask_fn=None) -> tuple[np.ndarray, np.ndarray]:
    """Confusion (n_units, K, 6, 5) and discordant (n_units, P, 2) counts for unit ids per cell.

    mask_fn(slice) -> bool array selects scored cells (None = all).
    """
    ref = load(cfg, "ref")
    maps = [load(cfg, f"map_{k}") for k in cfg.model_keys]
    k = len(maps)
    pairs = cfg.pairs
    n = len(ref)
    conf = np.zeros(n_units * k * 30, dtype=np.int64)
    disc = np.zeros(n_units * len(pairs) * 2, dtype=np.int64)
    for s in range(0, n, CHUNK):
        sl = slice(s, min(n, s + CHUNK))
        u = unit[sl].astype(np.int64)
        r = ref[sl].astype(np.int64) - 1
        mk = [m[sl].astype(np.int64) for m in maps]
        if mask_fn is not None:
            keep = mask_fn(sl)
            u, r, mk = u[keep], r[keep], [m[keep] for m in mk]
        for j in range(k):
            conf += np.bincount((u * k + j) * 30 + mk[j] * 5 + r, minlength=len(conf))
        correct = [m == (r + 1) for m in mk]
        for p, (a, b) in enumerate(pairs):
            base = (u * len(pairs) + p) * 2
            disc += np.bincount(base[correct[a] & ~correct[b]], minlength=len(disc))
            disc += np.bincount(base[correct[b] & ~correct[a]] + 1, minlength=len(disc))
    return conf.reshape(n_units, k, 6, 5), disc.reshape(n_units, len(pairs), 2)


def build_units(cfg: Config) -> dict:
    out = cfg.units_dir
    out.mkdir(parents=True, exist_ok=True)
    fdir = cfg.interim_dir / "frames"
    tiles = pd.read_parquet(fdir / "tiles_frame.parquet")
    tile = load(cfg, "tile")
    tconf, tdisc = unit_arrays(cfg, tile, len(tiles))
    np.save(out / "tiles_conf.npy", tconf)
    np.save(out / "tiles_disc.npy", tdisc)
    tmeta = tiles[["tile_id", "stratum", "n_cells", "cvpr_name", "cvpr_split", "cvpr_iou"]].copy()
    assert np.array_equal(tconf[:, 0].sum(axis=(1, 2)), tmeta["n_cells"].to_numpy())
    tmeta.to_parquet(out / "tiles_meta.parquet")

    chips = pd.read_parquet(fdir / "chips_frame.parquet")
    chip = load(cfg, "chip")
    purity = load(cfg, "purity")
    mins = purity_min_counts(cfg)
    m = len(chips)
    cconf = np.zeros((m, len(mins), cfg.n_models, 6, 5), dtype=np.int64)
    cdisc = np.zeros((m, len(mins), len(cfg.pairs), 2), dtype=np.int64)
    cmeta = chips[["chip_id", "tag", "complete", "n_cells"]].copy()
    for t, pmin in enumerate(mins):
        c, d = unit_arrays(cfg, chip, m, None if pmin == 0 else (lambda sl, pmin=pmin: purity[sl] >= pmin))
        cconf[:, t], cdisc[:, t] = c, d
        cmeta[f"n_scored_{cfg.purity_thresholds[t]}"] = c[:, 0].sum(axis=(1, 2))
        log.info("chips tau=%s done", cfg.purity_thresholds[t])
    np.save(out / "chips_conf.npy", cconf)
    np.save(out / "chips_disc.npy", cdisc)
    cmeta.to_parquet(out / "chips_meta.parquet")
    return {"tiles_conf_shape": list(tconf.shape), "chips_conf_shape": list(cconf.shape),
            "tiles_sum": int(tconf[:, 0].sum()), "chips_sum_tau0": int(cconf[:, 0, 0].sum()),
            "scored_cells_by_tau": {str(cfg.purity_thresholds[t]): int(cconf[:, t, 0].sum())
                                    for t in range(len(mins))}}
