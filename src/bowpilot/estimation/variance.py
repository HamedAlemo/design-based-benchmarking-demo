"""Linearization variance for stratified element and stratified one-stage cluster designs (PROTOCOL.md section 6).

Both functions take unit-level values with arbitrary trailing dimensions (e.g. (n, K, P)) and return the ratio
estimate R_hat and its variance V_hat with those trailing dimensions.

Element:  z_u = (y_u - R x_u) / X_hat,  V = sum_h N_h^2 (1 - n_h / N_h) s2_{z,h} / n_h
Cluster:  t_i = (Y_i - R X_i) / X_hat,  V = sum_h M_h^2 (1 - m_h / M_h) s2_{t,h} / m_h
s2 is the within-stratum sample variance (ddof = 1). A stratum sampled completely (n_h = N_h) contributes 0.
A stratum with n_h < 2 that is not sampled completely raises ValueError for element designs; for cluster designs
(e.g. a fixed realization with one PSU in a stratum) the variance is undefined and returned as NaN.
"""

from __future__ import annotations

import numpy as np

from bowpilot.contracts import StratumInfo


def strata_arrays(strata: list[StratumInfo]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(ids, N_h, n_h) as sorted int64 arrays."""
    s = sorted(strata, key=lambda x: x.stratum_id)
    return (np.array([x.stratum_id for x in s], dtype=np.int64),
            np.array([x.population_units for x in s], dtype=np.float64),
            np.array([x.sampled_units for x in s], dtype=np.float64))


def _stratified_var(z: np.ndarray, stratum: np.ndarray, ids: np.ndarray, pop: np.ndarray,
                    samp: np.ndarray, single: str = "raise") -> np.ndarray:
    """sum_h pop_h^2 (1 - samp_h / pop_h) s2_h / samp_h for unit scores z (n, ...)."""
    h = np.searchsorted(ids, stratum)
    if np.any(ids[np.minimum(h, len(ids) - 1)] != stratum):
        raise ValueError("sample stratum id not in strata list")
    nh_obs = np.bincount(h, minlength=len(ids)).astype(np.float64)
    if not np.array_equal(nh_obs, samp):
        raise ValueError(f"sampled units per stratum {nh_obs} differ from strata info {samp}")
    census = samp >= pop
    bad = (samp < 2) & ~census & (samp > 0)
    if bad.any():
        if single == "nan":
            return np.full(z.shape[1:], np.nan)
        raise ValueError(f"strata with n_h < 2 not sampled completely: {ids[bad]}")
    flat = z.reshape(z.shape[0], -1)
    nh = np.maximum(samp, 1.0)
    onehot = np.zeros((len(ids), flat.shape[0]))
    onehot[h, np.arange(flat.shape[0])] = 1.0
    s1 = onehot @ flat
    s2 = onehot @ (flat * flat)
    mean = s1 / nh[:, None]
    ss = s2 - nh[:, None] * mean * mean
    var_h = np.where((samp >= 2)[:, None], ss / np.maximum(samp - 1, 1)[:, None], 0.0)
    var_h = np.maximum(var_h, 0.0)
    coef = np.where(census | (samp == 0), 0.0, pop * pop * (1.0 - samp / pop) / nh)
    return (coef[:, None] * var_h).sum(axis=0).reshape(z.shape[1:])


def _ratio_and_scores(y: np.ndarray, x: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    wb = w.reshape((-1,) + (1,) * (y.ndim - 1))
    yh = (wb * y).sum(axis=0)
    xh = (wb * x).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.where(xh != 0, yh / np.where(xh != 0, xh, 1.0), np.nan)
        z = (y - r * x) / np.where(xh != 0, xh, np.nan)
    return r, xh, z


def var_ratio_element(y: np.ndarray, x: np.ndarray, w: np.ndarray, stratum: np.ndarray,
                      strata: list[StratumInfo]) -> tuple[np.ndarray, np.ndarray]:
    """Ratio estimate and linearized variance for a stratified element sample.

    y, x : (n, ...) unit values. w : (n,) design weights. stratum : (n,) stratum ids.
    strata : StratumInfo with N_h (cells) and n_h. Returns (R_hat, V_hat), each of shape y.shape[1:].
    """
    r, _, z = _ratio_and_scores(y, x, w)
    ids, pop, samp = strata_arrays(strata)
    v = _stratified_var(np.nan_to_num(z), stratum, ids, pop, samp)
    return r, np.where(np.isnan(r), np.nan, v)


def var_ratio_cluster(Y: np.ndarray, X: np.ndarray, w: np.ndarray, stratum: np.ndarray,  # noqa: N803
                      strata: list[StratumInfo]) -> tuple[np.ndarray, np.ndarray]:
    """Ratio estimate and linearized variance for a stratified one-stage cluster sample.

    Y, X : (m, ...) PSU totals over scored cells. w : (m,) PSU weights M_h / m_h. stratum : (m,) PSU strata.
    strata : StratumInfo with M_h (PSUs) and m_h. Returns (R_hat, V_hat) of shape Y.shape[1:].
    """
    r, _, t = _ratio_and_scores(Y, X, w)
    ids, pop, samp = strata_arrays(strata)
    v = _stratified_var(np.nan_to_num(t), stratum, ids, pop, samp, single="nan")
    return r, np.where(np.isnan(r), np.nan, v)
