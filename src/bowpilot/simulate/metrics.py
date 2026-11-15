"""Bias, MCSE, RMSE, SE ratio, coverage and CI width summaries (M5 "Summaries").

Reads the Monte Carlo Parquet files and the saved truth table (results/<extent>/truth/truth.parquet) as data. It never
imports the truth module and never touches the cell table: the comparison to truth happens only after estimation.

Outputs in results/<extent>/summary/ (Parquet and CSV): estimates_summary, ranking_summary, efficiency_summary,
domain_summary, area_summary.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from bowpilot.config import Config

log = logging.getLogger(__name__)
GROUP = ["arm", "budget", "tau", "model", "parameter"]


def load_mc(cfg: Config) -> pd.DataFrame:
    files = sorted((cfg.results_dir / "mc").glob("*_b*_t*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def load_truth(cfg: Config) -> pd.DataFrame:
    return pd.read_parquet(cfg.results_dir / "truth" / "truth.parquet")


def summarize_estimates(est: pd.DataFrame, truth: pd.DataFrame, n_rep: int, scope_for) -> pd.DataFrame:
    """est: rows of one kind with columns GROUP + estimate, se, ci_low, ci_high. scope_for(arm, tau) -> list of truth
    scopes to compare against."""
    tv = truth.set_index(["scope", "model", "parameter"])["value"]
    rows = []
    for key, g in est.groupby(GROUP, sort=True):
        arm, budget, tau, model, param = key
        e = g["estimate"].to_numpy()
        ok = ~np.isnan(e)
        r_def = int(ok.sum())
        e_ok = e[ok]
        se = g["se"].to_numpy()[ok]
        has_se = r_def > 0 and np.isfinite(se).any()
        lo, hi = g["ci_low"].to_numpy()[ok], g["ci_high"].to_numpy()[ok]
        for scope in scope_for(arm, tau):
            t = tv.get((scope, model, param), np.nan)
            row = {"arm": arm, "budget": budget, "tau": tau, "model": model, "parameter": param, "scope": scope,
                   "R": len(e), "R_def": r_def, "undefined_rate": 1 - r_def / len(e), "truth": t}
            if r_def >= 1:
                sd = float(e_ok.std(ddof=1)) if r_def > 1 else np.nan
                mean = float(e_ok.mean())
                row |= {"mean": mean, "bias": mean - t, "rel_bias": (mean - t) / t if t else np.nan,
                        "mcse_bias": sd / np.sqrt(r_def) if r_def > 1 else np.nan,
                        "rmse": float(np.sqrt(np.mean((e_ok - t) ** 2))), "emp_sd": sd}
                if has_se:
                    fin = np.isfinite(se)
                    cover = float(np.mean((lo[fin] <= t) & (t <= hi[fin])))
                    n_se = int(fin.sum())
                    row |= {"n_se": n_se, "mean_se": float(se[fin].mean()),
                            "se_ratio": float(se[fin].mean() / sd) if sd and sd > 0 else np.nan,
                            "coverage": cover, "mcse_coverage": float(np.sqrt(cover * (1 - cover) / n_se)),
                            "mean_ci_width": float((hi[fin] - lo[fin]).mean())}
            rows.append(row)
    return pd.DataFrame(rows)


def scope_rule(arm: str, tau: float) -> list[str]:
    if arm in ("B1", "A1"):
        return ["all", f"restricted_tau={tau}"]
    return ["all"]


def efficiency(est_sum: pd.DataFrame) -> pd.DataFrame:
    """H5: rho = mean CI width under D / under F, per model, class and budget, for UA_c and PA_c."""
    s = est_sum[(est_sum.scope == "all") & est_sum.parameter.str.match(r"^(UA|PA)_\d$")]
    d = s[s.arm == "D"].set_index(["budget", "model", "parameter"])
    f = s[s.arm == "F"].set_index(["budget", "model", "parameter"])
    j = d[["mean_ci_width", "R_def"]].merge(f[["mean_ci_width", "R_def"]], left_index=True, right_index=True,
                                            suffixes=("_D", "_F"), how="inner")
    j["rho"] = j["mean_ci_width_D"] / j["mean_ci_width_F"]
    j["labels_D"] = j.index.get_level_values("budget")
    j["labels_F"] = 3 * j["labels_D"]
    return j.reset_index()


def summarize_all(cfg: Config) -> dict:
    from bowpilot.simulate.ranking import summarize_ranking

    mc = load_mc(cfg)
    truth = load_truth(cfg)
    n_rep = cfg.mc_profile["replicates"]
    out = cfg.results_dir / "summary"
    out.mkdir(parents=True, exist_ok=True)
    est = mc[mc.kind == "estimate"]
    est_sum = summarize_estimates(est, truth, n_rep, scope_rule)
    ranking = summarize_ranking(mc, truth, cfg)
    eff = efficiency(est_sum)
    dom = mc[mc.kind.str.startswith("domain=")].copy()
    dom_rows = []
    for kind, g in dom.groupby("kind"):
        abbr = kind.split("=")[1]
        sres = summarize_estimates(g, truth, n_rep, lambda a, t, abbr=abbr: [f"state={abbr}"])
        sres["domain"] = abbr
        dom_rows.append(sres)
    # A0 per-state comparison: A0 pooled is not a domain estimator, so domain_summary holds D only (plus the H1
    # comparison in RESULTS.md uses A0's full-population bias).
    domain = pd.concat(dom_rows, ignore_index=True) if dom_rows else pd.DataFrame()
    ma = mc[mc.kind == "model_assisted"]
    area = summarize_estimates(ma, truth, n_rep, lambda a, t: ["all"])
    area["estimator"] = "model_assisted"
    so = est_sum[(est_sum.arm == "D") & est_sum.parameter.str.startswith("area_")].copy()
    so["estimator"] = "sample_only"
    area = pd.concat([area, so], ignore_index=True)
    maparea = truth[(truth.scope == "all") & truth.parameter.str.startswith("maparea_")]
    tables = {"estimates_summary": est_sum, "ranking_summary": ranking, "efficiency_summary": eff,
              "domain_summary": domain, "area_summary": area, "maparea_truth": maparea}
    for name, df in tables.items():
        df.to_parquet(out / f"{name}.parquet", index=False)
        df.to_csv(out / f"{name}.csv", index=False)
    log.info("summaries written: %s", {k: len(v) for k, v in tables.items()})
    return {k: len(v) for k, v in tables.items()}
