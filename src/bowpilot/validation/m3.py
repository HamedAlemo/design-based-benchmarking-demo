"""M3 validation driver (bowpilot validate-estimators).

1. Synthetic tables (same code and seeds as tests/test_estimators_synthetic.py), saved for the report.
2. R survey cross-check table.
3. Real-data check on the dev cell table: D at n = 1000 and A0w at T = 5, `draws` replicates each. Bias against
   the dev truth (read from results/dev/truth/truth.parquet after estimation) within 3 MCSE; OA coverage in
   [0.93, 0.97].
4. Bootstrap vs linearization on 200 synthetic draws.
Writes results/<extent>/validation/m3_*.csv and m3.json.
"""

from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd
from scipy.stats import norm

from bowpilot.config import Config
from bowpilot.estimation.bootstrap import bootstrap_confusions, bootstrap_se, raowu_weights
from bowpilot.estimation.estimate import RP, design_cluster
from bowpilot.sampling.arms import Context
from bowpilot.validation.r_check import run_r_check
from bowpilot.validation.synthetic import cluster_draw, cluster_population, element_population, run_cluster, run_element

log = logging.getLogger(__name__)
Z95 = 1.959963984540054


def synthetic(out) -> dict:
    pe, pc = element_population(), cluster_population()
    frames = [run_element(pe, n, 20000, 100 + n) for n in (500, 2000)]
    naive = []
    for m in (40, 80):
        a, b = run_cluster(pc, m, 20000, 200 + m)
        frames.append(a)
        naive.append(b)
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(out / "m3_synthetic.csv", index=False)
    pd.concat(naive).to_csv(out / "m3_synthetic_naive.csv", index=False)
    z = float(norm.ppf(1 - 0.01 / (2 * len(df))))
    bad = df[(df.resid_mcse.abs() > z) | (df.bias.abs() > 0.002)]
    over3 = df[df.bias.abs() > 3 * df.mcse]
    rng = np.random.default_rng(5)
    lin, boot = [], []
    for _ in range(200):
        s = cluster_draw(rng, pc, np.array([40, 40]))
        lin.append(design_cluster(s, []).se["OA"])
        bw = raowu_weights(rng, 1 / s.pi, s.stratum, s.strata, 200)
        boot.append(bootstrap_se(bootstrap_confusions(s.confusion, bw), ["OA"])["OA"])
    ratio = (np.mean(boot, axis=0) / np.mean(lin, axis=0)).tolist()
    return {"n_cells": len(df), "z_crit": z, "n_fail": len(bad), "n_raw_beyond_3mcse": len(over3),
            "raw_beyond_3mcse": over3[["design", "n", "model", "parameter", "bias", "pred_bias", "mcse",
                                       "resid_mcse"]].round(6).to_dict("records"),
            "oa": df[df.parameter == "OA"][["design", "n", "model", "bias", "mcse", "var_ratio", "coverage"]]
            .round(5).to_dict("records"),
            "naive_oa": pd.concat(naive).query("parameter == 'OA'")[["n", "model", "coverage"]].round(4)
            .to_dict("records"),
            "bootstrap_over_linear": ratio}


def real_data(cfg: Config, draws: int) -> pd.DataFrame:
    ctx = Context(cfg)
    rows = []
    T = 5 if 5 in cfg.budgets("A0") else 3  # noqa: N806
    for arm, budget, label in [("D", 1000, "D"), ("A0", T, "A0w")]:
        ss = np.random.SeedSequence([cfg.base_seed, 3, budget]).spawn(draws)
        for i, s in enumerate(ss):
            rng = np.random.Generator(np.random.PCG64(s))
            d = ctx.draw(arm, budget, rng)
            res = {lab: es for lab, _, es in ctx.evaluate(d)}
            es = res[label]
            for j, k in enumerate(cfg.model_keys):
                for p in RP.names:
                    rows.append((label, budget, i, k, p, float(es.est[p][j]), float(es.se[p][j])))
    return pd.DataFrame(rows, columns=["arm", "budget", "draw", "model", "parameter", "estimate", "se"])


def real_summary(df: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    tv = truth[truth.scope == "all"].set_index(["model", "parameter"])["value"]
    out = []
    for (arm, b, k, p), g in df.groupby(["arm", "budget", "model", "parameter"]):
        e, s = g.estimate.to_numpy(), g.se.to_numpy()
        ok = ~np.isnan(e)
        e, s = e[ok], s[ok]
        t = tv[(k, p)]
        sd = e.std(ddof=1)
        mcse = sd / np.sqrt(len(e))
        out.append({"arm": arm, "budget": b, "model": k, "parameter": p, "R_def": int(ok.sum()), "truth": t,
                    "bias": e.mean() - t, "mcse": mcse, "bias_mcse": (e.mean() - t) / mcse if mcse > 0 else 0.0,
                    "se_ratio": s.mean() / sd if sd > 0 else np.nan,
                    "coverage": float(np.mean(np.abs(e - t) <= Z95 * s))})
    return pd.DataFrame(out)


def run_m3(cfg: Config, draws: int = 5000) -> dict:
    out = cfg.results_dir / "validation"
    out.mkdir(parents=True, exist_ok=True)
    res = {"synthetic": synthetic(out)}
    log.info("synthetic done")
    r = run_r_check()
    r.to_csv(out / "m3_r_check.csv", index=False)
    res["r_check_max_rel_diff"] = {"estimate": float(r.rel_diff_estimate.max()), "se": float(r.rel_diff_se.max())}
    df = real_data(cfg, draws)
    truth = pd.read_parquet(cfg.results_dir / "truth" / "truth.parquet")   # read only after estimation
    summ = real_summary(df, truth)
    summ.to_csv(out / "m3_real_data.csv", index=False)
    oa = summ[summ.parameter == "OA"]
    res["real_data"] = {"draws": draws, "oa": oa.round(5).to_dict("records"),
                        "oa_bias_within_3mcse": bool((oa.bias_mcse.abs() <= 3).all()),
                        "oa_coverage_in_band": bool(oa.coverage.between(0.93, 0.97).all()),
                        "all_params_beyond_3mcse": summ[summ.bias_mcse.abs() > 3][
                            ["arm", "model", "parameter", "R_def", "bias", "mcse", "bias_mcse"]].round(6)
                        .to_dict("records")}
    (out / "m3.json").write_text(json.dumps(res, indent=2, default=str))
    return res
