"""Population truth. The ONLY module that computes metrics on the full cell table (CLAUDE.md invariant 2).

Uses the same estimation/params.py metric functions the estimators use, applied to population counts.
Scopes: all, state=<abbr>, restricted_tau=<t> (complete chips only, purity >= tau; the B1 target populations).
Outputs in results/<extent>/truth/: truth.parquet (scope, model, parameter, value), confusion.npz, rankings.json.
An independent raster code path recomputes the "all" confusion counts as a cross-check.
"""

from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd
import rasterio

from bowpilot.config import Config
from bowpilot.estimation.params import CLASSES, metrics_from_confusion
from bowpilot.grid import Grid
from bowpilot.population.cell_table import load
from bowpilot.population.units import purity_min_counts

log = logging.getLogger(__name__)
CHUNK = 20_000_000
RANK_METRICS = ["OA", "macroF1"] + [f"F1_{c}" for c in CLASSES]


def confusion_from_table(cfg: Config, mask_fn=None) -> np.ndarray:
    """(K, 6, 5) int64 population confusion counts over cells selected by mask_fn(slice) (None = all)."""
    ref = load(cfg, "ref")
    maps = [load(cfg, f"map_{k}") for k in cfg.model_keys]
    out = np.zeros((len(maps), 30), dtype=np.int64)
    for s in range(0, len(ref), CHUNK):
        sl = slice(s, min(len(ref), s + CHUNK))
        r = ref[sl].astype(np.int64) - 1
        keep = mask_fn(sl) if mask_fn is not None else slice(None)
        for j, m in enumerate(maps):
            out[j] += np.bincount((m[sl].astype(np.int64) * 5 + r)[keep], minlength=30)
    return out.reshape(len(maps), 6, 5)


def confusion_from_rasters(cfg: Config, grid: Grid) -> np.ndarray:
    """Independent cross-check: the same counts from the rasters by windowed reads (state > 0, ref_valid == 100)."""
    rd = cfg.rasters_dir
    out = np.zeros((cfg.n_models, 6, 5), dtype=np.int64)
    srcs = [rasterio.open(rd / f"map_{k}.tif") for k in cfg.model_keys]
    with rasterio.open(rd / "state.tif") as st, rasterio.open(rd / "ref_valid.tif") as va, \
            rasterio.open(rd / "ref_class.tif") as rc:
        for win in grid.windows(1024):
            pop = (st.read(1, window=win) > 0) & (va.read(1, window=win) == 100)
            if not pop.any():
                continue
            r = rc.read(1, window=win)[pop]
            for j, s in enumerate(srcs):
                m = s.read(1, window=win)[pop].astype(np.int64)
                out[j] += np.bincount(m * 5 + r.astype(np.int64) - 1, minlength=30).reshape(6, 5)
    for s in srcs:
        s.close()
    return out


def _rows(scope: str, conf: np.ndarray, keys: list[str]) -> list[dict]:
    met = metrics_from_confusion(conf)
    rows = []
    for j, k in enumerate(keys):
        for name, vals in met.items():
            rows.append({"scope": scope, "model": k, "parameter": name, "value": float(vals[j])})
    return rows


def rankings(conf: np.ndarray, keys: list[str], pairs: list[tuple[int, int]]) -> tuple[dict, list[dict]]:
    """True ranking (best first) per metric and true pairwise differences."""
    met = metrics_from_confusion(conf)
    rank = {m: [keys[i] for i in np.argsort(-met[m], kind="stable")] for m in RANK_METRICS}
    diffs = [{"scope": "all", "model": f"{keys[a]}|{keys[b]}", "parameter": f"diff_{m}",
              "value": float(met[m][a] - met[m][b])} for m in RANK_METRICS for a, b in pairs]
    return rank, diffs


def compute_truth(cfg: Config, grid: Grid) -> dict:
    keys = cfg.model_keys
    out = cfg.results_dir / "truth"
    out.mkdir(parents=True, exist_ok=True)
    confs: dict[str, np.ndarray] = {"all": confusion_from_table(cfg)}
    state = load(cfg, "state")
    for s in cfg.states:
        confs[f"state={s['abbr']}"] = confusion_from_table(cfg, lambda sl, c=s["code"]: state[sl] == c)
    chips_meta = pd.read_parquet(cfg.units_dir / "chips_meta.parquet")
    complete = chips_meta.sort_values("chip_id")["complete"].to_numpy()
    chip, purity = load(cfg, "chip"), load(cfg, "purity")
    for t, pmin in zip(cfg.purity_thresholds, purity_min_counts(cfg), strict=True):
        confs[f"restricted_tau={t}"] = confusion_from_table(
            cfg, lambda sl, pmin=pmin: complete[chip[sl]] & (purity[sl] >= pmin))
    rows = [r for scope, c in confs.items() for r in _rows(scope, c, keys)]
    rank, diffs = rankings(confs["all"], keys, cfg.pairs)
    df = pd.DataFrame(rows + diffs)
    df.to_parquet(out / "truth.parquet")
    np.savez(out / "confusion.npz", **{k.replace("=", "_"): v for k, v in confs.items()})
    (out / "rankings.json").write_text(json.dumps(rank, indent=2))
    raster = confusion_from_rasters(cfg, grid)
    cross = bool(np.array_equal(raster, confs["all"]))
    # unit array identities
    tiles_conf = np.load(cfg.units_dir / "tiles_conf.npy")
    chips_conf = np.load(cfg.units_dir / "chips_conf.npy", mmap_mode="r")
    unit_ok = {"tiles": bool(np.array_equal(tiles_conf.sum(axis=0), confs["all"])),
               "chips_tau0": bool(np.array_equal(np.asarray(chips_conf[:, 0]).sum(axis=0), confs["all"]))}
    for t, tau in enumerate(cfg.purity_thresholds):
        unit_ok[f"chips_complete_tau{tau}"] = bool(np.array_equal(
            np.asarray(chips_conf[complete, t]).sum(axis=0), confs[f"restricted_tau={tau}"]))
    log.info("truth cross-check %s, unit identities %s", cross, unit_ok)
    return {"cross_check_identical": cross, "unit_identities": unit_ok, "rankings": rank,
            "n_rows": len(df)}
