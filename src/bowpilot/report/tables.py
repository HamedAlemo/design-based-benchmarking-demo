"""Table 1, Table 2 and supplementary tables, generated from results/<extent>/ alone."""

from __future__ import annotations

import pandas as pd

from bowpilot.config import Config

ARM_ORDER = ["A0", "A0w", "A1", "B1", "B2", "C", "D", "D2", "E", "F"]


def table1(cfg: Config) -> pd.DataFrame:
    """True population metrics per model: OA, macroF1, UA_c, PA_c, area_c (scope all), plus state columns."""
    t = pd.read_parquet(cfg.results_dir / "truth" / "truth.parquet")
    params = ["OA", "macroF1"] + [f"{p}_{c}" for p in ("UA", "PA", "F1") for c in range(1, 6)] + \
        [f"area_{c}" for c in range(1, 6)] + [f"maparea_{c}" for c in range(1, 6)]
    t = t[t.parameter.isin(params) & t.scope.isin(["all"] + [f"state={s['abbr']}" for s in cfg.states])]
    wide = t.pivot_table(index="parameter", columns=["scope", "model"], values="value").reindex(params)
    return wide


def table2(cfg: Config) -> pd.DataFrame:
    s = pd.read_parquet(cfg.results_dir / "summary" / "estimates_summary.parquet")
    s = s[(s.scope == "all") & s.parameter.isin(["OA", "macroF1"])]
    cols = ["arm", "budget", "tau", "model", "parameter", "R_def", "truth", "bias", "mcse_bias", "rmse",
            "coverage", "se_ratio"]
    s = s[cols].copy()
    s["arm"] = pd.Categorical(s["arm"], ARM_ORDER, ordered=True)
    return s.sort_values(["parameter", "arm", "tau", "budget", "model"]).reset_index(drop=True)


def write_tables(cfg: Config) -> dict:
    out = cfg.results_dir / "tables"
    out.mkdir(parents=True, exist_ok=True)
    t1, t2 = table1(cfg), table2(cfg)
    t1.to_csv(out / "table1_truth.csv")
    t2.to_csv(out / "table2_bias_rmse_coverage.csv", index=False)
    for name in ["estimates_summary", "ranking_summary", "efficiency_summary", "domain_summary", "area_summary"]:
        pd.read_parquet(cfg.results_dir / "summary" / f"{name}.parquet").to_csv(out / f"supp_{name}.csv",
                                                                               index=False)
    return {"table1": t1, "table2": t2}
