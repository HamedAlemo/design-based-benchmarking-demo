"""Rao-Wu rescaling bootstrap within strata over cells or PSUs (Rao and Wu 1988; PROTOCOL.md section 6).

In stratum h with n_h units, draw n_h - 1 units with replacement. With lambda_h = sqrt(1 - f_h), f_h = n_h / N_h,
the bootstrap weight of unit u is
    w_u * (1 - lambda_h + lambda_h * n_h / (n_h - 1) * multiplicity_u)
(Rao and Wu 1988, rescaling with the finite population correction). When f_h is near 0 this equals the protocol's
w_u * n_h / (n_h - 1) * multiplicity_u; see docs/DECISIONS.md entry 20. Strata sampled completely (n_h = N_h) keep
fixed weights, since they contribute no sampling variance.
"""

from __future__ import annotations

import numpy as np

from bowpilot.contracts import StratumInfo
from bowpilot.estimation.params import metrics_from_confusion
from bowpilot.estimation.variance import strata_arrays


def raowu_weights(rng: np.random.Generator, w: np.ndarray, stratum: np.ndarray, strata: list[StratumInfo],
                  B: int) -> np.ndarray:  # noqa: N803
    """(B, n) bootstrap weights for n units with design weights w and stratum ids."""
    ids, pop, samp = strata_arrays(strata)
    h = np.searchsorted(ids, stratum)
    n = len(w)
    out = np.empty((B, n))
    for j in range(len(ids)):
        idx = np.nonzero(h == j)[0]
        nh = len(idx)
        if nh == 0:
            continue
        if nh >= pop[j] or nh < 2:
            out[:, idx] = w[idx]
            continue
        draws = rng.integers(0, nh, size=(B, nh - 1))
        mult = np.zeros((B, nh))
        np.add.at(mult, (np.arange(B)[:, None], draws), 1.0)
        lam = np.sqrt(1.0 - nh / pop[j])
        out[:, idx] = w[idx][None, :] * (1.0 - lam + lam * (nh / (nh - 1)) * mult)
    return out


def bootstrap_confusions(unit_conf: np.ndarray, boot_w: np.ndarray) -> np.ndarray:
    """(B, K, 6, 5) weighted confusions. unit_conf: (n, K, 6, 5) per-unit counts; boot_w: (B, n)."""
    n = unit_conf.shape[0]
    flat = unit_conf.reshape(n, -1).astype(np.float64)
    return (boot_w @ flat).reshape((boot_w.shape[0],) + unit_conf.shape[1:])


def bootstrap_se(boot_conf: np.ndarray, names: list[str] | None = None) -> dict[str, np.ndarray]:
    """Bootstrap SE (SD over replicates, ddof = 1, NaN replicates dropped) of every metric; arrays of shape (K,)."""
    m = metrics_from_confusion(boot_conf)
    out = {}
    for name, vals in m.items():
        if names is not None and name not in names:
            continue
        out[name] = nan_sd(vals)
    return out


def nan_sd(vals: np.ndarray) -> np.ndarray:
    """SD over axis 0 ignoring NaN (ddof = 1); NaN if fewer than 2 defined replicates."""
    ok = ~np.isnan(vals)
    cnt = ok.sum(axis=0)
    v = np.where(ok, vals, 0.0)
    mean = v.sum(axis=0) / np.maximum(cnt, 1)
    ss = (np.where(ok, vals - mean, 0.0) ** 2).sum(axis=0)
    return np.where(cnt >= 2, np.sqrt(ss / np.maximum(cnt - 1, 1)), np.nan)
