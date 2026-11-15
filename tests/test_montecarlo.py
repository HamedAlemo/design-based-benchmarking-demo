"""M5 driver tests on the tiny synthetic extent: completeness, reproducibility, NaN accounting, summaries."""

import copy
import hashlib

import numpy as np
import pandas as pd
import pytest

from bowpilot.config import Config


@pytest.fixture(scope="module")
def mc_cfg(tiny_population):
    cfg, _ = tiny_population
    new = Config(**{k: copy.deepcopy(v) for k, v in cfg.__dict__.items()})
    new.montecarlo["profiles"]["dev"] = {"replicates": 6, "bootstrap_subset": 2, "bootstrap_B": 20}
    from bowpilot.simulate.montecarlo import run_montecarlo

    run_montecarlo(new, n_jobs=2)
    return new


def _hash(df: pd.DataFrame) -> str:
    df = df.sort_values(list(df.columns)).reset_index(drop=True)
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).to_numpy().tobytes()).hexdigest()


def test_completeness(mc_cfg):
    from bowpilot.simulate.montecarlo import combos, file_complete, labels_for

    for arm, b in combos(mc_cfg):
        for lab, t in labels_for(mc_cfg, arm):
            assert file_complete(mc_cfg, lab, arm, b, t), (lab, b, t)


def test_reproducible(mc_cfg, tmp_path):
    from bowpilot.simulate.montecarlo import out_path, replicate_seeds, run_combo

    seeds = replicate_seeds(mc_cfg)
    for arm, b in [("D", 500), ("A1", 50)]:
        lab = arm
        tau = 0.0 if arm == "D" else 0.75
        before = _hash(pd.read_parquet(out_path(mc_cfg, lab, b, tau)))
        run_combo(mc_cfg, arm, b, seeds[(arm, b)], n_jobs=1)
        assert _hash(pd.read_parquet(out_path(mc_cfg, lab, b, tau))) == before


def test_nan_only_where_undefined(mc_cfg):
    from bowpilot.simulate.metrics import load_mc

    mc = load_mc(mc_cfg)
    est = mc[mc.kind == "estimate"]
    # NaN estimates only for ratio parameters that can be undefined (never OA or area_c)
    nan_params = set(est.loc[est.estimate.isna(), "parameter"])
    assert not nan_params & {"OA"} and not any(p.startswith("area_") for p in nan_params)
    s = pd.read_parquet(mc_cfg.results_dir / "summary" / "estimates_summary.parquet")
    assert (s.R_def <= s.R).all()
    assert np.allclose(s.undefined_rate, 1 - s.R_def / s.R)


def test_summaries_exist(mc_cfg):
    d = mc_cfg.results_dir / "summary"
    for name in ["estimates_summary", "ranking_summary", "efficiency_summary", "domain_summary", "area_summary"]:
        assert len(pd.read_parquet(d / f"{name}.parquet")) > 0, name
    r = pd.read_parquet(d / "ranking_summary.parquet")
    assert r.p_best_correct.between(0, 1).all()


def test_report_runs(mc_cfg):
    from bowpilot.report.run import run_report

    (mc_cfg.reports_dir / "figures").mkdir(parents=True, exist_ok=True)
    (mc_cfg.root / "docs").mkdir(exist_ok=True)
    (mc_cfg.root / "docs" / "HYPOTHESES.md").write_text("test")
    res = run_report(mc_cfg)
    figs = sorted((mc_cfg.root / "results" / "figures").glob("*.png"))
    assert len(figs) == 6 and len(sorted((mc_cfg.root / "results" / "figures").glob("*.pdf"))) == 6
    assert "### H1" in open(res["results_md"]).read()
