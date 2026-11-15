"""R survey cross-check (M3 item 4): one fixed stratified element sample and one fixed cluster sample (cell level),
exported to CSV, analysed with svydesign + svyratio, and compared with our estimates and SEs."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from bowpilot.config import REPO_ROOT
from bowpilot.contracts import ClusterSample, ElementSample, StratumInfo
from bowpilot.estimation.estimate import RP, design_cluster, design_element
from bowpilot.estimation.weighted import element_indicators
from bowpilot.validation.synthetic import cluster_draw, cluster_population, element_population

PARAMS = ["OA", "UA_2", "PA_4"]


def _element_sample(seed: int = 1) -> ElementSample:
    pop = element_population()
    rng = np.random.default_rng(seed)
    N_h = pop["N_h"]  # noqa: N806
    n_h = np.array([300, 250, 250, 200])
    idx = np.concatenate([rng.choice(np.nonzero(pop["stratum"] == h)[0], n_h[h], replace=False) for h in range(4)])
    st = pop["stratum"][idx]
    return ElementSample(idx, n_h[st] / N_h[st], st, [StratumInfo(h, int(N_h[h]), int(n_h[h])) for h in range(4)],
                         pop["ref"][idx], pop["maps"][idx])


def _cluster_cells(s: ClusterSample) -> pd.DataFrame:
    """Expand a cluster sample's confusion counts (model 0) into one row per scored cell."""
    rows = []
    for i in range(len(s.psu_index)):
        conf = s.confusion[i, 0]
        for m in range(6):
            for r in range(5):
                rows += [(int(s.psu_index[i]), int(s.stratum[i]), m, r + 1, 1 / s.pi[i])] * int(conf[m, r])
    return pd.DataFrame(rows, columns=["psu", "stratum", "map", "ref", "w"])


def run_r_check() -> pd.DataFrame:
    es_sample = _element_sample()
    es = design_element(es_sample, pairs=[])
    y, x = element_indicators(es_sample.maps[:, :1], es_sample.ref, RP)
    nh = {si.stratum_id: si.population_units for si in es_sample.strata}
    e = pd.DataFrame({"stratum": es_sample.stratum, "N_h": [nh[s] for s in es_sample.stratum],
                      "w": 1 / es_sample.pi})
    for p in PARAMS:
        e[f"y_{p}"], e[f"x_{p}"] = y[:, 0, RP.index(p)], x[:, 0, RP.index(p)]
    cpop = cluster_population()
    cs = cluster_draw(np.random.default_rng(2), cpop, np.array([20, 20]))
    cl = design_cluster(cs, pairs=[])
    c = _cluster_cells(cs)
    mh = {si.stratum_id: si.population_units for si in cs.strata}
    c["M_h"] = c["stratum"].map(mh)
    yc, xc = element_indicators(c["map"].to_numpy()[:, None].astype(np.uint8), c["ref"].to_numpy(), RP)
    for p in PARAMS:
        c[f"y_{p}"], c[f"x_{p}"] = yc[:, 0, RP.index(p)], xc[:, 0, RP.index(p)]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        e.to_csv(td / "e.csv", index=False)
        c.to_csv(td / "c.csv", index=False)
        subprocess.run(["Rscript", str(REPO_ROOT / "tests" / "r_survey_check.R"), str(td / "e.csv"),
                        str(td / "c.csv"), str(td / "out.csv")], check=True, capture_output=True)
        r = pd.read_csv(td / "out.csv")
    ours = {("element", p): (es.est[p][0], es.se[p][0]) for p in PARAMS}
    ours |= {("cluster", p): (cl.est[p][0], cl.se[p][0]) for p in PARAMS}
    r["ours_estimate"] = [ours[(d, p)][0] for d, p in zip(r.design, r.parameter, strict=True)]
    r["ours_se"] = [ours[(d, p)][1] for d, p in zip(r.design, r.parameter, strict=True)]
    r["rel_diff_estimate"] = (r.ours_estimate - r.estimate).abs() / r.estimate.abs()
    r["rel_diff_se"] = (r.ours_se - r.se).abs() / r.se.abs()
    return r
