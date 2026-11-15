"""Monte Carlo driver with checkpoint and resume (M5).

Seeds: SeedSequence(base_seed).spawn(J) gives one child per (drawing arm, budget) in the fixed order of COMBOS;
each child spawns one grandchild per replicate. The replicate's integer seed is
int(grandchild.generate_state(1, uint64)[0]) and its generator is Generator(PCG64(seed)); the seed is stored in every
row, so any replicate can be re-run from its row alone.

Each replicate draws once and evaluates every arm that reuses the draw (A0 -> A0w, A1 -> B1 at all tau, D -> E).
Output: one Parquet file per (arm, budget, tau) in results/<extent>/mc/, plus cvpr_actual.parquet.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from bowpilot.config import Config
from bowpilot.estimation.estimate import REPORTED, RP, EstimateSet, design_cluster, design_element_domain, naive_cluster
from bowpilot.estimation.model_assisted import poststratified_area
from bowpilot.estimation.naive import chip_mean_miou
from bowpilot.sampling.arms import DRAWING_ARMS, Context

log = logging.getLogger(__name__)
Z95 = 1.959963984540054
_CTX: dict[str, Context] = {}


def combos(cfg: Config) -> list[tuple[str, int]]:
    """(drawing arm, budget) in the fixed seed order."""
    return [(a, b) for a in DRAWING_ARMS for b in cfg.budgets(a)]


def replicate_seeds(cfg: Config) -> dict[tuple[str, int], list[int]]:
    root = np.random.SeedSequence(cfg.base_seed)
    R = cfg.mc_profile["replicates"]  # noqa: N806
    out = {}
    for (arm, b), child in zip(combos(cfg), root.spawn(len(combos(cfg))), strict=True):
        out[(arm, b)] = [int(g.generate_state(1, np.uint64)[0]) for g in child.spawn(R)]
    return out


def labels_for(cfg: Config, arm: str) -> list[tuple[str, float]]:
    """(arm label, tau) evaluated on a draw of `arm`."""
    if arm == "A0":
        return [("A0", 0.0), ("A0w", 0.0)]
    if arm == "A1":
        return ([("A1", float(t)) for t in cfg.arms["A1"]["purity_thresholds"]]
                + [("B1", float(t)) for t in cfg.arms["B1"]["purity_thresholds"]])
    if arm == "D":
        return [("D", 0.0), ("E", 0.0)]
    return [(arm, 0.0)]


def _ctx(cfg: Config) -> Context:
    key = str(cfg.cells_dir)
    if key not in _CTX:
        _CTX[key] = Context(cfg)
    return _CTX[key]


def _rows_from_set(label: str, tau: float, budget: int, rep: int, seed: int, es: EstimateSet, keys: list[str],
                   pairs: list[tuple[int, int]], only_model: int | None = None) -> list[dict]:
    rows = []
    base = {"arm": label, "budget": budget, "tau": tau, "replicate": rep, "seed": seed, "n_units": es.n_units,
            "n_cells_scored": es.n_cells_scored}
    for j, k in enumerate(keys):
        if only_model is not None and j != only_model:
            continue
        for name in REPORTED:
            e = float(es.est[name][j])
            s = float(es.se[name][j])
            rows.append(base | {"kind": "estimate", "model": k, "parameter": name, "estimate": e,
                                "se": s, "ci_low": e - Z95 * s, "ci_high": e + Z95 * s, "mcnemar_z": np.nan})
    for name, vals in es.pair_est.items():
        se = es.pair_se.get(name, np.full(len(vals), np.nan))
        z = es.pair_z.get(name, np.full(len(vals), np.nan))
        for p, (a, b) in enumerate(pairs):
            e, s = float(vals[p]), float(se[p])
            rows.append(base | {"kind": "pair", "model": f"{keys[a]}|{keys[b]}", "parameter": name, "estimate": e,
                                "se": s, "ci_low": e - Z95 * s, "ci_high": e + Z95 * s, "mcnemar_z": float(z[p])})
    return rows


def run_replicate(cfg: Config, arm: str, budget: int, rep: int, seed: int) -> list[dict]:
    ctx = _ctx(cfg)
    rng = np.random.Generator(np.random.PCG64(seed))
    d = ctx.draw(arm, budget, rng)
    prof = cfg.mc_profile
    boot = (rng, int(prof["bootstrap_B"])) if rep < int(prof["bootstrap_subset"]) else None
    keys, pairs = cfg.model_keys, cfg.pairs
    rows: list[dict] = []
    results = ctx.evaluate(d, boot)
    for j, (label, tau, es) in enumerate(results):
        only = j if arm == "F" else None
        rows += _rows_from_set(label, tau, budget, rep, seed, es, keys, [] if arm == "F" else pairs, only)
    if arm == "A1":   # chip-averaged mIoU, a secondary conventional metric
        for tau in cfg.arms["A1"]["purity_thresholds"]:
            s = ctx.chip_sample(d, float(tau))
            vals = chip_mean_miou(s.confusion)
            for j, k in enumerate(keys):
                rows.append({"arm": "A1", "budget": budget, "tau": float(tau), "replicate": rep, "seed": seed,
                             "n_units": len(s.psu_index), "n_cells_scored": int(s.confusion[:, 0].sum()),
                             "kind": "estimate", "model": k, "parameter": "chipmean_mIoU", "estimate": float(vals[j]),
                             "se": np.nan, "ci_low": np.nan, "ci_high": np.nan, "mcnemar_z": np.nan})
    if arm == "D":    # secondary: per-state domain estimates and model-assisted area
        s = d.element
        st = np.asarray(ctx.state[s.cell_index])
        base = {"arm": "D", "budget": budget, "tau": 0.0, "replicate": rep, "seed": seed, "mcnemar_z": np.nan}
        for sd in cfg.states:
            dom = st == sd["code"]
            est, se = design_element_domain(s, dom)
            for j, k in enumerate(keys):
                for p, name in enumerate(RP.names):
                    e, v = float(est[j, p]), float(se[j, p])
                    rows.append(base | {"kind": f"domain={sd['abbr']}", "model": k, "parameter": name,
                                        "estimate": e, "se": v, "ci_low": e - Z95 * v, "ci_high": e + Z95 * v,
                                        "n_units": int(dom.sum()), "n_cells_scored": int(dom.sum())})
        for j, k in enumerate(keys):
            est, se = poststratified_area(s.maps[:, j], s.ref, 1 / s.pi, s.stratum, s.strata, ctx.map_props[j])
            for c in range(5):
                e, v = float(est[c]), float(se[c])
                rows.append(base | {"kind": "model_assisted", "model": k, "parameter": f"area_{c + 1}",
                                    "estimate": e, "se": v, "ci_low": e - Z95 * v, "ci_high": e + Z95 * v,
                                    "n_units": len(s.ref), "n_cells_scored": len(s.ref)})
    return rows


def _run_chunk(cfg: Config, arm: str, budget: int, reps: list[int], seeds: list[int]) -> list[dict]:
    out = []
    for r, s in zip(reps, seeds, strict=True):
        out += run_replicate(cfg, arm, budget, r, s)
    return out


def out_path(cfg: Config, label: str, budget: int, tau: float) -> Path:
    return cfg.results_dir / "mc" / f"{label}_b{budget}_t{tau}.parquet"


def expected_rows(cfg: Config, label: str, arm: str, tau: float) -> int:
    """Rows per replicate for a label, times replicates."""
    k, p = cfg.n_models, len(cfg.pairs)
    R = cfg.mc_profile["replicates"]  # noqa: N806
    per = k * len(REPORTED)
    if arm == "F":
        return R * per
    if label in ("A0", "A1", "E"):
        per += p * 7                          # diff_OA + point diffs of macroF1 and F1_c
        if label == "A1":
            per += k                          # chip-mean mIoU
    else:
        per += p * 7
    if label == "D":
        per += len(cfg.states) * k * len(RP.names) + k * 5
    return R * per


def file_complete(cfg: Config, label: str, arm: str, budget: int, tau: float) -> bool:
    p = out_path(cfg, label, budget, tau)
    if not p.exists():
        return False
    import pyarrow.parquet as pq

    return pq.ParquetFile(p).metadata.num_rows == expected_rows(cfg, label, arm, tau)


def run_combo(cfg: Config, arm: str, budget: int, seeds: list[int], n_jobs: int) -> float:
    t0 = time.time()
    R = len(seeds)  # noqa: N806
    nj = n_jobs if n_jobs > 0 else max(1, (__import__("os").cpu_count() or 2) - 1)
    chunks = np.array_split(np.arange(R), max(1, min(R, nj * 4)))
    parts = Parallel(n_jobs=nj, backend="loky")(
        delayed(_run_chunk)(cfg, arm, budget, list(map(int, c)), [seeds[i] for i in c]) for c in chunks if len(c))
    df = pd.DataFrame([r for part in parts for r in part])
    for label, tau in labels_for(cfg, arm):
        sub = df[(df.arm == label) & (df.tau == tau)].sort_values(["replicate", "kind", "model", "parameter"])
        p = out_path(cfg, label, budget, tau)
        p.parent.mkdir(parents=True, exist_ok=True)
        sub.reset_index(drop=True).to_parquet(p, index=False)
        exp = expected_rows(cfg, label, arm, tau)
        if len(sub) != exp:
            log.warning("%s: %d rows, expected %d", p.name, len(sub), exp)
    return time.time() - t0


def run_cvpr_actual(cfg: Config) -> None:
    ctx = _ctx(cfg)
    s = ctx.actual_cvpr_test_split()
    if len(s.psu_index) == 0:
        log.warning("no matched CVPR test tiles in this extent")
        return
    rows = []
    for label, es in [("A0", naive_cluster(s, cfg.pairs)), ("A0w", design_cluster(s, cfg.pairs))]:
        rows += _rows_from_set(label, 0.0, len(s.psu_index), 0, -1, es, cfg.model_keys, cfg.pairs)
    pd.DataFrame(rows).to_parquet(cfg.results_dir / "mc" / "cvpr_actual.parquet", index=False)


def run_montecarlo(cfg: Config, resume: bool = False, arms: list[str] | None = None, n_jobs: int = -1,
                   summarize: bool = True) -> dict:
    seeds = replicate_seeds(cfg)
    (cfg.results_dir / "mc").mkdir(parents=True, exist_ok=True)
    runtimes = {}
    rt_path = cfg.results_dir / "mc" / "runtimes.json"
    if rt_path.exists():
        runtimes = json.loads(rt_path.read_text())
    for arm, b in combos(cfg):
        if arms and arm not in arms:
            continue
        if resume and all(file_complete(cfg, lab, arm, b, t) for lab, t in labels_for(cfg, arm)):
            log.info("skip %s b=%d (complete)", arm, b)
            continue
        log.info("run %s b=%d (%d replicates)", arm, b, len(seeds[(arm, b)]))
        runtimes[f"{arm}_b{b}"] = round(run_combo(cfg, arm, b, seeds[(arm, b)], n_jobs), 1)
        rt_path.write_text(json.dumps(runtimes, indent=2))
        log.info("%s b=%d done in %.0fs", arm, b, runtimes[f"{arm}_b{b}"])
    run_cvpr_actual(cfg)
    if summarize:
        from bowpilot.simulate.metrics import summarize_all

        summarize_all(cfg)
    return runtimes
