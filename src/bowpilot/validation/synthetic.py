"""Synthetic test populations for M3 estimator validation (software tests only, not study results).

Element case: N = 20,000 cells, 4 strata, 3 models with class-specific error rates, a rare class (4) at about 2%.
Cluster case: 300 PSUs of unequal size in 2 strata, with a PSU-level random effect on correctness (intra-cluster
correlation). Truth is computed directly from the synthetic population here, never by the estimators.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bowpilot.contracts import ClusterSample, ElementSample, StratumInfo
from bowpilot.estimation.estimate import RP, design_cluster, design_element, naive_cluster
from bowpilot.estimation.params import ratio_from_confusion
from bowpilot.estimation.weighted import cluster_totals, element_confusion, element_indicators

PAIRS = [(0, 1), (0, 2), (1, 2)]
REF_P = np.array([0.10, 0.35, 0.40, 0.02, 0.13])         # class 4 is the rare class (~2%)
ERR = np.array([[0.05, 0.10, 0.10, 0.40, 0.15],          # per-model, per-class error rate
                [0.08, 0.06, 0.15, 0.30, 0.25],
                [0.03, 0.15, 0.08, 0.55, 0.10]])


def _maps_from_ref(rng: np.random.Generator, ref: np.ndarray, err: np.ndarray, shift: np.ndarray | None = None
                   ) -> np.ndarray:
    """(N, K) model maps: correct with prob 1 - err[k, r] (+ optional per-cell logit shift), else a random wrong
    class in 0..5 (class 0 = no prediction, rarely)."""
    n = len(ref)
    k = err.shape[0]
    maps = np.empty((n, k), dtype=np.uint8)
    for j in range(k):
        e = err[j, ref - 1]
        if shift is not None:
            lo = np.log(e / (1 - e)) + shift
            e = 1 / (1 + np.exp(-lo))
        wrong = rng.random(n) < e
        alt = rng.choice(np.array([0, 1, 2, 3, 4, 5]), size=n, p=[0.04, 0.24, 0.24, 0.24, 0.0, 0.24])
        alt = np.where(alt == ref, 4, alt)  # never "wrong" with the reference class itself
        alt = np.where(alt == ref, 0, alt)
        maps[:, j] = np.where(wrong, alt, ref)
    return maps


def element_population(seed: int = 7, N: int = 20_000) -> dict:  # noqa: N803
    """Synthetic element population with 4 strata; stratum 3 is enriched for the rare class."""
    rng = np.random.default_rng(seed)
    stratum = rng.choice(4, size=N, p=[0.4, 0.3, 0.2, 0.1]).astype(np.int32)
    probs = np.tile(REF_P, (4, 1))
    probs[3] = [0.05, 0.2, 0.3, 0.15, 0.3]
    probs[0] = [0.15, 0.4, 0.4, 0.0, 0.05]
    probs /= probs.sum(axis=1, keepdims=True)
    ref = np.empty(N, dtype=np.uint8)
    for h in range(4):
        idx = np.nonzero(stratum == h)[0]
        ref[idx] = rng.choice(np.arange(1, 6), size=len(idx), p=probs[h])
    maps = _maps_from_ref(rng, ref, ERR)
    return {"ref": ref, "maps": maps, "stratum": stratum, "N_h": np.bincount(stratum, minlength=4)}


def cluster_population(seed: int = 11, n_psu: int = 300, sd_effect: float = 0.8) -> dict:
    """300 PSUs, sizes 20..400 cells, 2 strata; PSU random effects on class mix and correctness."""
    rng = np.random.default_rng(seed)
    sizes = rng.integers(20, 401, size=n_psu)
    stratum = np.repeat([0, 1], n_psu // 2).astype(np.int32)
    k = ERR.shape[0]
    conf = np.zeros((n_psu, k, 6, 5), dtype=np.int64)
    disc = np.zeros((n_psu, len(PAIRS), 2), dtype=np.int64)
    for i in range(n_psu):
        p = rng.dirichlet(REF_P * 20 + (0.5 if stratum[i] else 0.1))
        ref = rng.choice(np.arange(1, 6), size=sizes[i], p=p).astype(np.uint8)
        shift = np.full(sizes[i], rng.normal(0, sd_effect))
        maps = _maps_from_ref(rng, ref, ERR, shift)
        conf[i] = element_confusion(maps, ref, np.ones(sizes[i])).astype(np.int64)
        correct = maps == ref[:, None]
        disc[i] = [[np.sum(correct[:, a] & ~correct[:, b]), np.sum(correct[:, b] & ~correct[:, a])] for a, b in PAIRS]
    return {"conf": conf, "disc": disc, "stratum": stratum, "M_h": np.bincount(stratum)}


def ratio_bias_2nd(Yu: np.ndarray, Xu: np.ndarray, strat: np.ndarray, pop_h: np.ndarray, samp_h: np.ndarray
                   ) -> np.ndarray:
    """Second-order bias of the ratio estimator under stratified SRS: (R V(X_hat) - Cov(Y_hat, X_hat)) / X^2.

    Yu, Xu : (units, K, P) population unit values (cells or PSU totals). Returns (K, P). See DECISIONS.md entry 22.
    """
    Y, X = Yu.sum(0), Xu.sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        R = Y / X  # noqa: N806
    V = np.zeros_like(R)  # noqa: N806
    C = np.zeros_like(R)  # noqa: N806
    for h in range(len(pop_h)):
        m = strat == h
        Mh, mh = float(pop_h[h]), float(samp_h[h])  # noqa: N806
        y, x = Yu[m], Xu[m]
        f = Mh ** 2 * (1 - mh / Mh) / mh
        V += f * x.var(0, ddof=1)
        C += f * ((x - x.mean(0)) * (y - y.mean(0))).sum(0) / (Mh - 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (R * V - C) / X ** 2


def _summ(est: np.ndarray, se: np.ndarray, truth: np.ndarray, names: list[str], label: str, n: int,
          pred: np.ndarray | None = None) -> pd.DataFrame:
    """est, se: (R, K, P); truth (K, P); pred (K, P) predicted second-order ratio bias."""
    rows = []
    z = 1.959963984540054
    for k in range(est.shape[1]):
        for p, name in enumerate(names):
            e, s, t = est[:, k, p], se[:, k, p], truth[k, p]
            ok = ~np.isnan(e)
            r = ok.sum()
            if r < 2:
                continue
            e, s = e[ok], s[ok]
            sd = e.std(ddof=1)
            cover = np.mean((e - z * s <= t) & (t <= e + z * s))
            rows.append({"design": label, "n": n, "model": k, "parameter": name, "R_def": int(r), "truth": t,
                         "mean": e.mean(), "bias": e.mean() - t, "mcse": sd / np.sqrt(r),
                         "bias_mcse": (e.mean() - t) / (sd / np.sqrt(r)) if sd > 0 else 0.0,
                         "pred_bias": float(pred[k, p]) if pred is not None else 0.0,
                         "var_ratio": np.mean(s ** 2) / sd ** 2 if sd > 0 else np.nan, "coverage": cover})
    df = pd.DataFrame(rows)
    df["resid_mcse"] = (df["bias"] - df["pred_bias"]) / df["mcse"]
    return df


def run_element(pop: dict, n: int, draws: int, seed: int) -> pd.DataFrame:
    """Proportional-plus-minimum stratified SRS of cells; design-based ratio estimates."""
    N_h = pop["N_h"]  # noqa: N806
    n_h = np.maximum(np.round(n * N_h / N_h.sum()).astype(int), 2)
    n_h[0] += n - n_h.sum()
    strata = [StratumInfo(h, int(N_h[h]), int(n_h[h])) for h in range(4)]
    idx_by = [np.nonzero(pop["stratum"] == h)[0] for h in range(4)]
    truth = ratio_from_confusion(element_confusion(pop["maps"], pop["ref"], np.ones(len(pop["ref"]))), RP)
    rng = np.random.default_rng(seed)
    est = np.empty((draws, 3, len(RP.names)))
    se = np.empty_like(est)
    for d in range(draws):
        idx = np.concatenate([rng.choice(idx_by[h], n_h[h], replace=False) for h in range(4)])
        st = pop["stratum"][idx]
        s = ElementSample(idx, n_h[st] / N_h[st], st, strata, pop["ref"][idx], pop["maps"][idx])
        es = design_element(s, pairs=[])
        est[d] = np.stack([es.est[nm] for nm in RP.names], axis=1)
        se[d] = np.stack([es.se[nm] for nm in RP.names], axis=1)
    yu, xu = element_indicators(pop["maps"], pop["ref"], RP)
    pred = ratio_bias_2nd(yu, xu, pop["stratum"], N_h, n_h)
    return _summ(est, se, truth, RP.names, "element", n, pred)


def cluster_draw(rng: np.random.Generator, pop: dict, m_h: np.ndarray) -> ClusterSample:
    M_h = pop["M_h"]  # noqa: N806
    idx = np.concatenate([rng.choice(np.nonzero(pop["stratum"] == h)[0], m_h[h], replace=False)
                          for h in range(len(M_h))])
    st = pop["stratum"][idx]
    strata = [StratumInfo(h, int(M_h[h]), int(m_h[h])) for h in range(len(M_h))]
    return ClusterSample(idx, m_h[st] / M_h[st], st, strata, pop["conf"][idx], pop["disc"][idx])


def run_cluster(pop: dict, m: int, draws: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified SRS of PSUs (m / 2 per stratum); design-cluster and naive pooled estimates."""
    m_h = np.array([m // 2, m - m // 2])
    truth = ratio_from_confusion(pop["conf"].sum(axis=0).astype(float), RP)
    rng = np.random.default_rng(seed)
    est = np.empty((draws, 3, len(RP.names)))
    se = np.empty_like(est)
    nest = np.empty_like(est)
    nse = np.empty_like(est)
    for d in range(draws):
        s = cluster_draw(rng, pop, m_h)
        es = design_cluster(s, pairs=[])
        ns = naive_cluster(s, pairs=[])
        est[d] = np.stack([es.est[nm] for nm in RP.names], axis=1)
        se[d] = np.stack([es.se[nm] for nm in RP.names], axis=1)
        nest[d] = np.stack([ns.est[nm] for nm in RP.names], axis=1)
        nse[d] = np.stack([ns.se[nm] for nm in RP.names], axis=1)
    Yu, Xu = cluster_totals(pop["conf"], RP)  # noqa: N806
    pred = ratio_bias_2nd(Yu, Xu, pop["stratum"], pop["M_h"], m_h)
    return (_summ(est, se, truth, RP.names, "cluster", m, pred),
            _summ(nest, nse, truth, RP.names, "cluster_naive", m))
