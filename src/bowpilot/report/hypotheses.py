"""Mechanical evaluation of the frozen criteria in docs/HYPOTHESES.md against the summary tables.

Every function returns (verdict, parts, tables): parts maps each numbered condition to True/False, and tables holds
the deciding numbers as DataFrames. Interpretation choices (stated in RESULTS.md):
- Design-set conditions are applied to each design arm separately ("every design arm must satisfy it").
- "Every budget" means every budget of the arm in the extent's configuration.
- Element-level percentages ("at least 95% of combinations") count (model, class, budget) cells per arm with
  R_def >= 0.95 R.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DESIGN = ["C", "D", "D2", "F", "A0w", "B2"]
CONVENTIONAL = ["A0", "A1", "E"]
CLASS_RE = r"^(UA|PA|area)_\d$"


def _verdict(parts: dict[str, bool]) -> str:
    v = list(parts.values())
    if all(v):
        return "Supported"
    if not any(v):
        return "Not supported"
    return "Partially supported"


def _tol(df: pd.DataFrame, floor: float) -> pd.Series:
    return np.maximum(2 * df["mcse_bias"].fillna(0), floor)


def h1_design_ok(est: pd.DataFrame, arms: list[str]) -> tuple[bool, pd.DataFrame, pd.DataFrame]:
    s = est[(est.scope == "all") & est.arm.isin(arms)]
    main = s[s.parameter.isin(["OA", "macroF1"])].copy()
    main["tol"] = _tol(main, 0.002)
    main["ok"] = main["bias"].abs() <= main["tol"]
    cls = s[s.parameter.str.match(CLASS_RE) & (s.R_def >= 0.95 * s.R)].copy()
    cls["tol"] = _tol(cls, 0.005)
    cls["ok"] = cls["bias"].abs() <= cls["tol"]
    share = cls.groupby("arm")["ok"].agg(["mean", "size"]).rename(columns={"mean": "share_ok", "size": "n_cells"})
    share["ok"] = share["share_ok"] >= 0.95
    ok = bool(main["ok"].all()) and bool(share["ok"].all())
    return ok, main, share.reset_index()


def h1(est: pd.DataFrame) -> tuple[str, dict, dict]:
    ok1, main, share = h1_design_ok(est, DESIGN)
    conv = est[(est.scope == "all") & est.arm.isin(CONVENTIONAL) & est.parameter.isin(["OA", "macroF1"])].copy()
    conv["tol"] = _tol(conv, 0.01)
    conv["biased"] = conv["bias"].abs() > conv["tol"]
    parts = {"1 design arms unbiased": ok1, "2 a conventional arm biased": bool(conv["biased"].any())}
    return _verdict(parts), parts, {"design_main": main, "design_class_share": share, "conventional": conv}


def h2(est: pd.DataFrame) -> tuple[str, dict, dict]:
    s = est[(est.scope == "all")]
    d = s[s.arm.isin(DESIGN) & (s.parameter == "OA")].copy()
    d["ok"] = d["coverage"].between(0.93, 0.97)
    cls = s[s.arm.isin(DESIGN) & s.parameter.str.match(r"^(UA|PA)_\d$") & (s.R_def >= 0.95 * s.R)].copy()
    cls["ok"] = cls["coverage"] >= 0.90
    share = cls.groupby("arm")["ok"].agg(["mean", "size"]).rename(columns={"mean": "share_ok", "size": "n_cells"})
    share["ok"] = share["share_ok"] >= 0.90
    a0 = s[(s.arm == "A0") & (s.parameter == "OA")].copy()
    a0["under"] = a0["coverage"] < 0.90
    per_model = a0.groupby("model")["under"].all()
    parts = {"1a design OA coverage in [0.93, 0.97]": bool(d["ok"].all()),
             "1b design UA/PA coverage >= 0.90 for >= 90%": bool(share["ok"].all()),
             "2 A0 OA coverage < 0.90 at every T for >= 2 models": int(per_model.sum()) >= 2}
    return _verdict(parts), parts, {"design_oa": d, "design_class_share": share.reset_index(), "a0": a0}


def h3(est: pd.DataFrame, rank: pd.DataFrame, truth: pd.DataFrame) -> tuple[str, dict, dict]:
    oa = rank[rank.metric == "OA"].copy()
    d = oa[oa.arm.isin(DESIGN)].copy()
    d["ok"] = d["type_s"] <= 0.025 + 2 * d["mcse_type_s"].fillna(0)
    conv = rank[rank.arm.isin(CONVENTIONAL) & rank.metric.isin(["OA", "macroF1"])].copy()
    c500 = rank[(rank.arm == "C") & (rank.budget == 500)].set_index("metric")["p_best_correct"]
    conv["p_best_C500"] = conv["metric"].map(c500)
    conv["best_gap"] = conv["p_best_C500"] - conv["p_best_correct"]
    conv["type_s_gt_0.05"] = (conv["metric"] == "OA") & (conv["type_s"] > 0.05)
    conv["best_lower_0.10"] = conv["best_gap"] >= 0.10
    cond2 = bool((conv["type_s_gt_0.05"] | conv["best_lower_0.10"]).any())
    parts = {"1 design Type S <= 0.025 + 2 MCSE": bool(d["ok"].all()), "2 a conventional arm fails": cond2}
    t = truth[(truth.scope == "all") & (truth.parameter == "OA")].set_index("model")["value"]
    gaps = {f"{a}|{b}": float(t[a] - t[b]) for i, a in enumerate(t.index) for b in t.index[i + 1:]}
    note = None
    if not cond2 and min(abs(g) for g in gaps.values()) > 0.02:
        note = "H0 outcome: no conventional arm failed although all true OA gaps exceed 0.02."
    return _verdict(parts), parts, {"design_type_s": d, "conventional": conv, "true_oa_gaps": gaps, "note": note}


def h4(est: pd.DataFrame) -> tuple[str, dict, dict]:
    b1 = est[(est.arm == "B1") & (est.parameter == "OA")]
    full = b1[b1.scope == "all"].copy()
    piv = full.pivot_table(index=["budget", "model"], columns="tau", values="bias")
    mono = (piv[0.75] < piv[0.9]) & (piv[0.9] < piv[1.0])
    t1 = full[full.tau == 1.0].copy()
    t1["tol"] = _tol(t1, 0.01)
    t1["ok"] = t1["bias"] > t1["tol"]
    restricted = b1[b1.scope.str.startswith("restricted")].copy()
    restricted["tol"] = _tol(restricted, 0.002)
    restricted["ok"] = restricted["bias"].abs() <= restricted["tol"]
    b2_ok, b2_main, b2_share = h1_design_ok(est, ["B2"])
    parts = {"1a B1 OA bias increases with tau": bool(mono.all()), "1b B1(1.0) bias > max(2 MCSE, 0.01)":
             bool(t1["ok"].all()), "2 B1 consistent for restricted truth": bool(restricted["ok"].all()),
             "3 B2 meets H1 design criterion": b2_ok}
    return _verdict(parts), parts, {"bias_by_tau": piv.reset_index(), "b1_tau1": t1, "restricted": restricted,
                                    "b2_main": b2_main, "b2_share": b2_share}


def h5(eff: pd.DataFrame) -> tuple[str, dict, dict]:
    med = eff.groupby("budget")["rho"].median()
    parts = {f"median rho <= 1.25 at n = {n}": bool(med.get(n, np.nan) <= 1.25) for n in (1000, 2000)}
    worst = eff.sort_values("rho", ascending=False).head(5)
    return _verdict(parts), parts, {"median_rho": med.reset_index(), "max_rho": float(eff["rho"].max()),
                                    "weakest": worst, "cost_ratio_F_over_D": 3}


def h0(est: pd.DataFrame, rank: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    r = rank[rank.arm.isin(CONVENTIONAL) & rank.metric.isin(["OA", "macroF1"])]
    p = r.pivot_table(index=["arm", "budget", "tau"], columns="metric", values="p_ranking_exact").reset_index()
    conv = est[(est.scope == "all") & est.arm.isin(CONVENTIONAL) & est.parameter.isin(["OA", "macroF1"])].copy()
    conv["biased"] = conv["bias"].abs() > _tol(conv, 0.01)
    biased = conv.groupby(["arm", "budget", "tau"])["biased"].any().rename("h1_biased").reset_index()
    p = p.merge(biased, on=["arm", "budget", "tau"], how="left")
    p["label"] = np.where((p[["OA", "macroF1"]].min(axis=1) >= 0.95) & p["h1_biased"],
                          "ranking robust, absolute values biased", "")
    return p
