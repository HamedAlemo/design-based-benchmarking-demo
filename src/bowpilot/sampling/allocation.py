"""Minimum plus Neyman or proportional allocation with caps (PROTOCOL.md section 5, M4 item 1)."""

from __future__ import annotations

import numpy as np


def largest_remainder(total: int, weights: np.ndarray) -> np.ndarray:
    """Integer split of `total` proportional to weights (>= 0), rounding by the largest-remainder method.
    Ties in the remainder go to the lower index (deterministic)."""
    w = np.asarray(weights, dtype=np.float64)
    if total <= 0 or w.sum() <= 0:
        return np.zeros(len(w), dtype=np.int64)
    exact = total * w / w.sum()
    base = np.floor(exact).astype(np.int64)
    rest = total - int(base.sum())
    order = np.lexsort((np.arange(len(w)), -(exact - base)))
    base[order[:rest]] += 1
    return base


def allocate(n: int, N_h: np.ndarray, m_min_base: int, weights: np.ndarray) -> np.ndarray:  # noqa: N803
    """Allocate n units to strata.

    1. Every non-empty stratum gets m_min = min(m_min_base, floor(n / (2 H))), but at least 2 (capped at N_h).
    2. The remainder is split in proportion to `weights`, largest-remainder rounding.
    3. Each n_h is capped at N_h; any excess is redistributed over uncapped strata in proportion to weights,
       repeating until settled.
    Returns int64 n_h summing to n (requires n <= sum N_h).
    """
    N_h = np.asarray(N_h, dtype=np.int64)  # noqa: N806
    weights = np.asarray(weights, dtype=np.float64)
    if n > N_h.sum():
        raise ValueError(f"n = {n} exceeds population {N_h.sum()}")
    live = N_h > 0
    H = int(live.sum())  # noqa: N806
    m_min = max(2, min(m_min_base, n // (2 * H)))
    n_h = np.where(live, np.minimum(m_min, N_h), 0).astype(np.int64)
    if n_h.sum() > n:
        raise ValueError(f"n = {n} too small for the minimum of {m_min} in {H} strata")
    remaining = n - int(n_h.sum())
    while remaining > 0:
        open_ = n_h < N_h
        w = np.where(open_, weights, 0.0)
        if w.sum() <= 0:                       # weights exhausted: fall back to remaining capacity
            w = np.where(open_, (N_h - n_h).astype(np.float64), 0.0)
        add = largest_remainder(remaining, w)
        new = np.minimum(n_h + add, N_h)
        remaining -= int((new - n_h).sum())
        n_h = new
    assert n_h.sum() == n
    return n_h


def neyman_weights_D(N_h: np.ndarray, levels: list[str], error_rates: dict[str, float]) -> np.ndarray:  # noqa: N802,N803
    """N_h S_h with S_h = sqrt(e (1 - e)) by agreement level."""
    e = np.array([error_rates[lv] for lv in levels])
    return np.asarray(N_h, dtype=np.float64) * np.sqrt(e * (1 - e))
