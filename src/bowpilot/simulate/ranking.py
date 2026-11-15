"""Best-model selection, Kendall tau-b, pairwise decision classes and Type S (M5 ranking_summary).

Per replicate and metric (OA, macroF1, F1_c):
- best correct: the model with the highest estimate equals the true best model
- Kendall tau-b between the estimated and true orderings of the K models
- per pair: correct-significant (CI excludes 0, right sign), not significant, Type S (CI excludes 0, wrong sign),
  and sign flip (point estimate has the wrong sign, regardless of significance)
Significance: design arms use the pair's design CI; naive arms use McNemar |z| > 1.96 for OA and have no test for
macroF1 or F1_c (decision classes NaN there). Arm F has independent samples per model, so its OA pair SE is
sqrt(se_k^2 + se_l^2) from the per-model estimates. Decisions with no SE (bootstrap metrics outside the bootstrap
subset) count only toward the sign-flip rate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bowpilot.config import Config

Z95 = 1.959963984540054
METRICS = ["OA", "macroF1"] + [f"F1_{c}" for c in range(1, 6)]
NAIVE = {"A0", "A1", "E"}


def kendall_tau_b(x: np.ndarray, y: np.ndarray) -> float:
    n = len(x)
    s = n1 = n2 = 0
    tot = n * (n - 1) // 2
    for i in range(n):
        for j in range(i + 1, n):
            a, b = np.sign(x[i] - x[j]), np.sign(y[i] - y[j])
            s += a * b
            n1 += a == 0
            n2 += b == 0
    den = np.sqrt((tot - n1) * (tot - n2))
    return float(s / den) if den > 0 else np.nan


def summarize_ranking(mc: pd.DataFrame, truth: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    keys = cfg.model_keys
    pairs = cfg.pairs
    tv = truth[truth.scope == "all"].set_index(["model", "parameter"])["value"]
    est = mc[(mc.kind == "estimate") & mc.parameter.isin(METRICS)]
    pr = mc[(mc.kind == "pair")]
    rows = []
    for (arm, budget, tau), g in est.groupby(["arm", "budget", "tau"]):
        gp = pr[(pr.arm == arm) & (pr.budget == budget) & (pr.tau == tau)]
        for metric in METRICS:
            t = np.array([tv[(k, metric)] for k in keys])
            true_best = int(np.argmax(t))
            piv = g[g.parameter == metric].pivot_table(index="replicate", columns="model", values="estimate")[keys]
            sepiv = g[g.parameter == metric].pivot_table(index="replicate", columns="model", values="se",
                                                         dropna=False)
            vals = piv.to_numpy()
            ok = ~np.isnan(vals).any(axis=1)
            best = np.argmax(np.where(np.isnan(vals), -np.inf, vals), axis=1)
            taus = [kendall_tau_b(v, t) for v in vals[ok]]
            dec = {"correct_sig": [], "not_sig": [], "type_s": [], "sign_flip": []}
            gpm = gp[gp.parameter == f"diff_{metric}"]
            for a, b in pairs:
                true_d = t[a] - t[b]
                if arm == "F":
                    d = vals[:, a] - vals[:, b]
                    if metric == "OA":
                        se = np.sqrt(sepiv[keys[a]].to_numpy() ** 2 + sepiv[keys[b]].to_numpy() ** 2)
                    else:
                        se = np.full(len(d), np.nan)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        z = d / se
                else:
                    sub = gpm[gpm.model == f"{keys[a]}|{keys[b]}"].sort_values("replicate")
                    d = sub["estimate"].to_numpy()
                    if arm in NAIVE:
                        z = sub["mcnemar_z"].to_numpy() if metric == "OA" else np.full(len(d), np.nan)
                    else:
                        with np.errstate(divide="ignore", invalid="ignore"):   # SE 0 only for a census draw
                            z = d / sub["se"].to_numpy()
                dok = ~np.isnan(d)
                dec["sign_flip"] += list(np.sign(d[dok]) != np.sign(true_d))
                zok = np.isfinite(z)
                sig = np.abs(z[zok]) > Z95
                right = np.sign(d[zok]) == np.sign(true_d)
                dec["correct_sig"] += list(sig & right)
                dec["type_s"] += list(sig & ~right)
                dec["not_sig"] += list(~sig)
            n_dec = len(dec["correct_sig"])
            rows.append({"arm": arm, "budget": budget, "tau": tau, "metric": metric, "R": len(vals),
                         "R_def": int(ok.sum()), "true_best": keys[true_best],
                         "p_best_correct": float(np.mean(best[ok] == true_best)) if ok.any() else np.nan,
                         "kendall_tau_b": float(np.nanmean(taus)) if taus else np.nan,
                         "p_ranking_exact": float(np.mean([tb == 1.0 for tb in taus])) if taus else np.nan,
                         "n_decisions": n_dec,
                         "correct_sig": float(np.mean(dec["correct_sig"])) if n_dec else np.nan,
                         "not_sig": float(np.mean(dec["not_sig"])) if n_dec else np.nan,
                         "type_s": float(np.mean(dec["type_s"])) if n_dec else np.nan,
                         "mcse_type_s": float(np.sqrt(np.mean(dec["type_s"]) * (1 - np.mean(dec["type_s"])) / n_dec))
                         if n_dec else np.nan,
                         "sign_flip": float(np.mean(dec["sign_flip"])) if dec["sign_flip"] else np.nan})
    return pd.DataFrame(rows)
