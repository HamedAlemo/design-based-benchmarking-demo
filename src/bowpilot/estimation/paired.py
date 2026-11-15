"""Design-based paired differences between models k and l (PROTOCOL.md section 6).

OA: d_u = 1[m_k(u) = r(u)] - 1[m_l(u) = r(u)], estimated as a ratio with x_u = 1 (x = scored cells for clusters),
with the design's linearized variance. macroF1 and F1_c differences: Rao-Wu bootstrap SE of the difference.
"""

from __future__ import annotations

import numpy as np

from bowpilot.contracts import StratumInfo
from bowpilot.estimation.bootstrap import nan_sd
from bowpilot.estimation.params import CLASSES, metrics_from_confusion
from bowpilot.estimation.variance import var_ratio_cluster, var_ratio_element


def diff_oa_element(maps: np.ndarray, ref: np.ndarray, w: np.ndarray, stratum: np.ndarray,
                    strata: list[StratumInfo], pairs: list[tuple[int, int]]) -> tuple[np.ndarray, np.ndarray]:
    """(P,) estimates and SEs of OA_k - OA_l for each pair, element design."""
    correct = (maps == ref[:, None]).astype(np.float64)
    y = np.stack([correct[:, k] - correct[:, j] for k, j in pairs], axis=1)
    r, v = var_ratio_element(y, np.ones_like(y), w, stratum, strata)
    return r, np.sqrt(v)


def diff_oa_cluster(disc: np.ndarray, n_scored: np.ndarray, w: np.ndarray, stratum: np.ndarray,
                    strata: list[StratumInfo]) -> tuple[np.ndarray, np.ndarray]:
    """(P,) estimates and SEs of OA_k - OA_l, cluster design. disc (m, P, 2); n_scored (m,) scored cells per PSU."""
    y = (disc[:, :, 0] - disc[:, :, 1]).astype(np.float64)
    x = np.repeat(n_scored.astype(np.float64)[:, None], y.shape[1], axis=1)
    r, v = var_ratio_cluster(y, x, w, stratum, strata)
    return r, np.sqrt(v)


PAIR_METRICS = ["macroF1"] + [f"F1_{c}" for c in CLASSES]


def diff_metrics_point(conf: np.ndarray, pairs: list[tuple[int, int]]) -> dict[str, np.ndarray]:
    """Point differences (P,) of macroF1 and F1_c from a weighted confusion (K, 6, 5)."""
    m = metrics_from_confusion(conf)
    return {name: np.array([m[name][k] - m[name][j] for k, j in pairs]) for name in PAIR_METRICS}


def diff_metrics_boot(boot_conf: np.ndarray, pairs: list[tuple[int, int]]) -> dict[str, np.ndarray]:
    """Bootstrap SEs (P,) of macroF1 and F1_c differences from (B, K, 6, 5) bootstrap confusions."""
    m = metrics_from_confusion(boot_conf)
    return {name: nan_sd(np.stack([m[name][:, k] - m[name][:, j] for k, j in pairs], axis=1))
            for name in PAIR_METRICS}
