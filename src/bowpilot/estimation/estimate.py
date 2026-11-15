"""Full estimate sets for one sample: every model, every parameter, SEs and pairwise OA differences.

Results are plain dicts: est[name] and se[name] are (K,) arrays (se NaN where the estimator gives none);
pair_est / pair_se / pair_z are (P,) arrays for diff_OA (z only for naive arms). Bootstrap SEs for nonlinear
parameters and their differences are added only when `boot` (rng, B) is given.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from bowpilot.contracts import ClusterSample, ElementSample
from bowpilot.estimation.bootstrap import bootstrap_confusions, bootstrap_se, raowu_weights
from bowpilot.estimation.naive import discordant_from_cells, naive_diff_oa, naive_estimates
from bowpilot.estimation.paired import diff_metrics_boot, diff_metrics_point, diff_oa_cluster, diff_oa_element
from bowpilot.estimation.params import NONLINEAR, metrics_from_confusion, ratio_params
from bowpilot.estimation.variance import var_ratio_cluster, var_ratio_element
from bowpilot.estimation.weighted import (
    cluster_confusion,
    cluster_totals,
    element_confusion,
    element_indicators,
    element_onehot,
)

RP = ratio_params(include_area=True)
REPORTED = ["OA", "macroF1", "mIoU"] + [f"{p}_{c}" for p in ("UA", "PA", "F1", "IoU", "area") for c in range(1, 6)]


@dataclass
class EstimateSet:
    est: dict[str, np.ndarray]
    se: dict[str, np.ndarray]
    pair_est: dict[str, np.ndarray] = field(default_factory=dict)   # "diff_OA", "diff_macroF1", "diff_F1_c"
    pair_se: dict[str, np.ndarray] = field(default_factory=dict)
    pair_z: dict[str, np.ndarray] = field(default_factory=dict)
    n_units: int = 0
    n_cells_scored: int = 0
    conf: np.ndarray | None = None


def _empty_se(k: int) -> dict[str, np.ndarray]:
    return {name: np.full(k, np.nan) for name in REPORTED}


def _fill(es: EstimateSet, conf_w: np.ndarray, r: np.ndarray, v: np.ndarray) -> None:
    pts = metrics_from_confusion(conf_w)
    for name in REPORTED:
        es.est[name] = pts[name]
    for p, name in enumerate(RP.names):
        es.est[name] = r[:, p]
        es.se[name] = np.sqrt(v[:, p])


def design_element(s: ElementSample, pairs: list[tuple[int, int]], boot: tuple | None = None) -> EstimateSet:
    """Design-based estimates for a stratified element sample (arms C, D, D2, F)."""
    w = 1.0 / s.pi
    k = s.maps.shape[1]
    y, x = element_indicators(s.maps, s.ref, RP)
    r, v = var_ratio_element(y, x, w, s.stratum, s.strata)
    conf = element_confusion(s.maps, s.ref, w)
    es = EstimateSet({}, _empty_se(k), n_units=len(w), n_cells_scored=len(w), conf=conf)
    _fill(es, conf, r, v)
    if pairs:
        d, se = diff_oa_element(s.maps, s.ref, w, s.stratum, s.strata, pairs)
        es.pair_est["diff_OA"], es.pair_se["diff_OA"] = d, se
        for name, val in diff_metrics_point(conf, pairs).items():
            es.pair_est[f"diff_{name}"] = val
    if boot is not None:
        rng, B = boot
        bw = raowu_weights(rng, w, s.stratum, s.strata, B)
        unit = element_onehot(s.maps, s.ref).reshape(len(w), k, 6, 5)
        _add_boot(es, bootstrap_confusions(unit, bw), pairs)
    return es


def design_cluster(s: ClusterSample, pairs: list[tuple[int, int]], boot: tuple | None = None) -> EstimateSet:
    """Design-based estimates for a stratified one-stage cluster sample (arms A0w, B1, B2)."""
    w = 1.0 / s.pi
    k = s.confusion.shape[1]
    Y, X = cluster_totals(s.confusion, RP)  # noqa: N806
    r, v = var_ratio_cluster(Y, X, w, s.stratum, s.strata)
    conf = cluster_confusion(s.confusion, w)
    n_scored = s.confusion[:, 0].sum(axis=(-2, -1))
    es = EstimateSet({}, _empty_se(k), n_units=len(w), n_cells_scored=int(n_scored.sum()), conf=conf)
    _fill(es, conf, r, v)
    if pairs:
        d, se = diff_oa_cluster(s.discordant, n_scored, w, s.stratum, s.strata)
        es.pair_est["diff_OA"], es.pair_se["diff_OA"] = d, se
        for name, val in diff_metrics_point(conf, pairs).items():
            es.pair_est[f"diff_{name}"] = val
    if boot is not None:
        rng, B = boot
        bw = raowu_weights(rng, w, s.stratum, s.strata, B)
        _add_boot(es, bootstrap_confusions(s.confusion, bw), pairs)
    return es


def _add_boot(es: EstimateSet, boot_conf: np.ndarray, pairs: list[tuple[int, int]]) -> None:
    for name, val in bootstrap_se(boot_conf, NONLINEAR).items():
        es.se[name] = val
    if pairs:
        for name, val in diff_metrics_boot(boot_conf, pairs).items():
            es.pair_se[f"diff_{name}"] = val


def naive_from_confusion(conf: np.ndarray, disc: np.ndarray, n_units: int) -> EstimateSet:
    """Naive pooled estimates from a pooled unweighted confusion (K, 6, 5) and pooled McNemar counts (P, 2)."""
    est, se = naive_estimates(conf)
    k = conf.shape[0]
    total = float(conf[0].sum())
    es = EstimateSet({n: est[n] for n in REPORTED}, _empty_se(k), n_units=n_units, n_cells_scored=int(total),
                     conf=conf)
    for name, val in se.items():
        es.se[name] = val
    d, s_, z = naive_diff_oa(disc[:, 0], disc[:, 1], total)
    es.pair_est["diff_OA"], es.pair_se["diff_OA"], es.pair_z["diff_OA"] = d, s_, z
    return es


def naive_cluster(s: ClusterSample, pairs: list[tuple[int, int]]) -> EstimateSet:
    """Arms A0, A1: pool all scored cells of the selected PSUs, ignore weights and clustering."""
    conf = s.confusion.sum(axis=0).astype(np.float64)
    es = naive_from_confusion(conf, s.discordant.sum(axis=0), len(s.psu_index))
    for name, val in diff_metrics_point(conf, pairs).items():
        es.pair_est[f"diff_{name}"] = val
    return es


def naive_element(s: ElementSample, pairs: list[tuple[int, int]]) -> EstimateSet:
    """Arm E: an element sample analysed with equal weights."""
    conf = element_confusion(s.maps, s.ref, np.ones(len(s.ref)))
    es = naive_from_confusion(conf, discordant_from_cells(s.maps, s.ref, pairs), len(s.ref))
    for name, val in diff_metrics_point(conf, pairs).items():
        es.pair_est[f"diff_{name}"] = val
    return es


def design_element_domain(s: ElementSample, domain: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Domain estimates of the ratio parameters for cells with domain == True (e.g. one state), using the full
    sample's design (y and x multiplied by the domain indicator). Returns (est, se), each (K, P) in RP order."""
    w = 1.0 / s.pi
    y, x = element_indicators(s.maps, s.ref, RP)
    d = domain.astype(np.float64)[:, None, None]
    r, v = var_ratio_element(y * d, x * d, w, s.stratum, s.strata)
    return r, np.sqrt(v)
