"""Naive pooled estimates as practiced: unweighted counts, binomial SE, McNemar on pooled pixels.

Used by A0 and A1 (pooled cells of selected PSUs) and E (D's element sample with equal weights).
Binomial SE sqrt(p (1 - p) / n), with n = all scored cells for OA, cells mapped c for UA_c, cells of reference c
for PA_c. No SE for area_c, F1_c, IoU_c, macroF1, mIoU.
"""

from __future__ import annotations

import warnings

import numpy as np

from bowpilot.estimation.params import CLASSES, metrics_from_confusion


def binomial_se(p: np.ndarray, n: np.ndarray) -> np.ndarray:
    p = np.asarray(p, dtype=np.float64)
    n = np.asarray(n, dtype=np.float64)
    out = np.full(np.broadcast(p, n).shape, np.nan)
    np.divide(p * (1 - p), n, out=out, where=n > 0)
    return np.sqrt(out)


def naive_estimates(conf: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Point estimates and binomial SEs from a pooled unweighted confusion (K, 6, 5).

    Returns (estimates, ses): name -> (K,) arrays. ses only has OA, UA_c, PA_c.
    """
    est = metrics_from_confusion(conf)
    total = conf.sum(axis=(-2, -1))
    se = {"OA": binomial_se(est["OA"], total)}
    for c in CLASSES:
        se[f"UA_{c}"] = binomial_se(est[f"UA_{c}"], conf[..., c, :].sum(axis=-1))
        se[f"PA_{c}"] = binomial_se(est[f"PA_{c}"], conf[..., :, c - 1].sum(axis=-1))
    return est, se


def mcnemar(b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """McNemar z = (b - c) / sqrt(b + c); z = 0 when b + c = 0. b: k right & l wrong, c: l right & k wrong."""
    b = np.asarray(b, dtype=np.float64)
    c = np.asarray(c, dtype=np.float64)
    s = b + c
    out = np.zeros(np.broadcast(b, c).shape)
    np.divide(b - c, np.sqrt(s), out=out, where=s > 0)
    return out


def naive_diff_oa(b: np.ndarray, c: np.ndarray, n: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pooled OA difference (b - c) / n, its McNemar-consistent SE sqrt(b + c) / n, and McNemar z.

    With these definitions estimate / SE equals the McNemar z, so the CI excludes 0 exactly when |z| > 1.96.
    """
    b = np.asarray(b, dtype=np.float64)
    c = np.asarray(c, dtype=np.float64)
    d = (b - c) / n if n > 0 else np.full(b.shape, np.nan)
    se = np.sqrt(b + c) / n if n > 0 else np.full(b.shape, np.nan)
    return d, se, mcnemar(b, c)


def discordant_from_cells(maps: np.ndarray, ref: np.ndarray, pairs: list[tuple[int, int]]) -> np.ndarray:
    """(P, 2) McNemar counts from cell-level maps (n, K) and ref (n,)."""
    correct = maps == ref[:, None]
    return np.array([[np.sum(correct[:, k] & ~correct[:, j]), np.sum(correct[:, j] & ~correct[:, k])]
                     for k, j in pairs], dtype=np.int64)


def chip_mean_miou(conf: np.ndarray) -> np.ndarray:
    """Chip-averaged mIoU (K,): mIoU per chip from its own confusion (m, K, 6, 5), then the mean over chips.

    Classes absent from a chip's map and reference (IoU undefined) are skipped within the chip (nanmean), as in
    common practice; chips with no scored cells are skipped.
    """
    m = metrics_from_confusion(conf)
    iou = np.stack([m[f"IoU_{c}"] for c in CLASSES], axis=-1)  # (m, K, 5)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        per_chip = np.nanmean(iou, axis=-1)
        return np.nanmean(per_chip, axis=0)
