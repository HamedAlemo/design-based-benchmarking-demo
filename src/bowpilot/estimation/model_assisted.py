"""Post-stratified (model-assisted) area estimator using a model map as auxiliary data (PROTOCOL.md section 6).

area_c(PS, k) = sum_i W_i p_hat(r = c | m_k = i), with W_i the known population proportion of map class i
(i = 0..5) and p_hat a design-weighted ratio. Linearized SE: z_u = sum_i W_i (y_iu - R_i x_iu) / X_i_hat with
y_iu = 1[m = i, r = c], x_iu = 1[m = i], then the stratified element variance of z.
"""

from __future__ import annotations

import numpy as np

from bowpilot.contracts import N_MAP_CLASSES, StratumInfo
from bowpilot.estimation.params import CLASSES
from bowpilot.estimation.variance import _stratified_var, strata_arrays


def poststratified_area(map_k: np.ndarray, ref: np.ndarray, w: np.ndarray, stratum: np.ndarray,
                        strata: list[StratumInfo], W: np.ndarray) -> tuple[np.ndarray, np.ndarray]:  # noqa: N803
    """Estimates and SEs (5,) of area_c for c = 1..5. map_k (n,), ref (n,), W (6,) known map proportions."""
    n = len(ref)
    x = (map_k[:, None] == np.arange(N_MAP_CLASSES)[None, :]).astype(np.float64)          # (n, 6)
    yc = (ref[:, None] == np.array(CLASSES)[None, :]).astype(np.float64)                    # (n, 5)
    y = x[:, :, None] * yc[:, None, :]                                                      # (n, 6, 5)
    xh = (w[:, None] * x).sum(axis=0)                                                       # (6,)
    yh = (w[:, None, None] * y).sum(axis=0)                                                 # (6, 5)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = yh / xh[:, None]
    used = W > 0
    if np.any(xh[used] == 0):
        return np.full(5, np.nan), np.full(5, np.nan)
    r = np.where(used[:, None], r, 0.0)
    est = (W[:, None] * r).sum(axis=0)
    safe_x = np.where(xh > 0, xh, 1.0)
    z = (W[None, :, None] * (y - r[None] * x[:, :, None]) / safe_x[None, :, None])
    z = np.where(used[None, :, None], z, 0.0).sum(axis=1)                                   # (n, 5)
    ids, pop, samp = strata_arrays(strata)
    v = _stratified_var(z, stratum, ids, pop, samp)
    assert z.shape == (n, 5)
    return est, np.sqrt(v)
