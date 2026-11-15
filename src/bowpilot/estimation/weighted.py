"""Weighted error matrices and per-unit indicator totals for element and cluster designs.

Shapes: n sampled cells, m sampled PSUs, K models, P ratio parameters.
"""

from __future__ import annotations

import numpy as np

from bowpilot.contracts import N_MAP_CLASSES, N_REF_CLASSES
from bowpilot.estimation.params import RatioParams

NCELL = N_MAP_CLASSES * N_REF_CLASSES  # 30


def cell_codes(maps: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """(n, K) int64 flat confusion-cell code m * 5 + (r - 1) per cell and model."""
    return maps.astype(np.int64) * N_REF_CLASSES + (ref.astype(np.int64)[:, None] - 1)


def element_confusion(maps: np.ndarray, ref: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted confusion (K, 6, 5) from an element sample. maps (n, K) 0..5, ref (n,) 1..5, w (n,)."""
    n, k = maps.shape
    codes = cell_codes(maps, ref) + np.arange(k)[None, :] * NCELL
    c = np.bincount(codes.ravel(), weights=np.repeat(w, k), minlength=k * NCELL)
    return c.reshape(k, N_MAP_CLASSES, N_REF_CLASSES)


def element_onehot(maps: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """(n, K * 30) float64 one-hot confusion membership of each cell, per model."""
    n, k = maps.shape
    codes = cell_codes(maps, ref) + np.arange(k)[None, :] * NCELL
    u = np.zeros((n, k * NCELL))
    u[np.arange(n)[:, None], codes] = 1.0
    return u


def cluster_confusion(conf: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted confusion (K, 6, 5) = sum_i w_i conf_i. conf (m, K, 6, 5), w (m,)."""
    return np.einsum("i,ikab->kab", w.astype(np.float64), conf.astype(np.float64))


def element_indicators(maps: np.ndarray, ref: np.ndarray, rp: RatioParams) -> tuple[np.ndarray, np.ndarray]:
    """Per-cell indicators y, x of shape (n, K, P)."""
    m = maps.astype(np.intp)
    r = ref.astype(np.intp)[:, None] - 1
    y = rp.ay[:, m, r]  # (P, n, K)
    x = rp.ax[:, m, r]
    return np.moveaxis(y, 0, -1), np.moveaxis(x, 0, -1)


def cluster_totals(conf: np.ndarray, rp: RatioParams) -> tuple[np.ndarray, np.ndarray]:
    """Per-PSU totals Y, X of shape (m, K, P) from conf (m, K, 6, 5)."""
    c = conf.astype(np.float64)
    return np.einsum("ikab,pab->ikp", c, rp.ay), np.einsum("ikab,pab->ikp", c, rp.ax)
