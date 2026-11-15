"""M6 driver: figures, tables and the RESULTS draft, from results/<extent>/ alone (plus rasters for Figure 5)."""

from __future__ import annotations

import logging

import pandas as pd

from bowpilot.config import Config
from bowpilot.report import figures, results_md, tables
from bowpilot.simulate.metrics import load_mc

log = logging.getLogger(__name__)


def run_report(cfg: Config, study_area: bool = True) -> dict:
    sd = cfg.results_dir / "summary"
    est = pd.read_parquet(sd / "estimates_summary.parquet")
    rank = pd.read_parquet(sd / "ranking_summary.parquet")
    eff = pd.read_parquet(sd / "efficiency_summary.parquet")
    truth = pd.read_parquet(cfg.results_dir / "truth" / "truth.parquet")
    mc = load_mc(cfg)
    cv_path = cfg.results_dir / "mc" / "cvpr_actual.parquet"
    cvpr = pd.read_parquet(cv_path) if cv_path.exists() else None
    tables.write_tables(cfg)
    figures.fig1_estimates(cfg, mc, truth, cvpr)
    figures.fig2_ranking(cfg, rank, figures._cells_per_draw(mc))
    figures.fig3_coverage(cfg, est)
    figures.fig4_bridge(cfg, est)
    if study_area:
        figures.fig5_study_area(cfg)
    figures.fig6_efficiency(cfg, eff)
    path = results_md.write_draft(cfg)
    log.info("report written: %s", path)
    return {"results_md": path}
