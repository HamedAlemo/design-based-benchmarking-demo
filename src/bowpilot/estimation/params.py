"""Parameter definitions as (y, x) indicator pairs; metrics from a confusion matrix.

Confusion matrices have shape (..., 6, 5): rows are map classes 0..5 (0 = no prediction), columns are reference
classes 1..5 (column j holds reference class j + 1). Entries are (weighted) cell counts or proportions.

Every ratio parameter R = Y / X is defined by two coefficient matrices A_y, A_x of shape (6, 5):
    y_u = A_y[m_u, r_u - 1],  x_u = A_x[m_u, r_u - 1]
so a cell's indicators, a PSU's totals (sum of A * confusion) and the population value all use the same definition.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bowpilot.contracts import N_MAP_CLASSES, N_REF_CLASSES

CLASSES = list(range(1, N_REF_CLASSES + 1))
NONLINEAR = [f"F1_{c}" for c in CLASSES] + [f"IoU_{c}" for c in CLASSES] + ["macroF1", "mIoU"]


@dataclass(frozen=True)
class RatioParams:
    """A set of ratio parameters. names: (P,); ay, ax: (P, 6, 5) float64 coefficient matrices."""

    names: list[str]
    ay: np.ndarray
    ax: np.ndarray

    def index(self, name: str) -> int:
        return self.names.index(name)


def _diag() -> np.ndarray:
    a = np.zeros((N_MAP_CLASSES, N_REF_CLASSES))
    for c in CLASSES:
        a[c, c - 1] = 1.0
    return a


def ratio_params(include_area: bool = True) -> RatioParams:
    """OA, UA_c, PA_c and (optionally) area_c, in that order.

    OA:     y = 1[m = r],             x = 1
    UA_c:   y = 1[m = c and r = c],   x = 1[m = c]
    PA_c:   y = 1[m = c and r = c],   x = 1[r = c]
    area_c: y = 1[r = c],             x = 1
    """
    names, ay, ax = ["OA"], [_diag()], [np.ones((N_MAP_CLASSES, N_REF_CLASSES))]
    for c in CLASSES:
        y = np.zeros((N_MAP_CLASSES, N_REF_CLASSES))
        y[c, c - 1] = 1.0
        xu = np.zeros_like(y)
        xu[c, :] = 1.0
        xp = np.zeros_like(y)
        xp[:, c - 1] = 1.0
        names += [f"UA_{c}", f"PA_{c}"]
        ay += [y, y]
        ax += [xu, xp]
    if include_area:
        for c in CLASSES:
            y = np.zeros((N_MAP_CLASSES, N_REF_CLASSES))
            y[:, c - 1] = 1.0
            names.append(f"area_{c}")
            ay.append(y)
            ax.append(np.ones((N_MAP_CLASSES, N_REF_CLASSES)))
    return RatioParams(names, np.stack(ay), np.stack(ax))


def _div(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a / b with NaN (never 0 or inf) where b == 0."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    out = np.full(np.broadcast(a, b).shape, np.nan)
    np.divide(a, b, out=out, where=b != 0)
    return out


def metrics_from_confusion(conf: np.ndarray) -> dict[str, np.ndarray]:
    """Every parameter from a (..., 6, 5) confusion matrix. Zero denominators give NaN.

    macroF1 and mIoU are the plain means over the five classes; they are NaN if any class-level value is NaN.
    Also returns maparea_c (map-implied proportion p_c+, over all cells including class 0 rows).
    """
    conf = np.asarray(conf, dtype=np.float64)
    total = conf.sum(axis=(-2, -1))
    diag = np.stack([conf[..., c, c - 1] for c in CLASSES], axis=-1)        # (..., 5)
    row = np.stack([conf[..., c, :].sum(axis=-1) for c in CLASSES], axis=-1)  # p_c+
    col = conf.sum(axis=-2)                                                    # p_+c
    out: dict[str, np.ndarray] = {"OA": _div(diag.sum(axis=-1), total)}
    ua, pa = _div(diag, row), _div(diag, col)
    f1 = _div(2 * diag, row + col)
    iou = _div(diag, row + col - diag)
    area, maparea = _div(col, total[..., None]), _div(row, total[..., None])
    for i, c in enumerate(CLASSES):
        out[f"UA_{c}"] = ua[..., i]
        out[f"PA_{c}"] = pa[..., i]
        out[f"F1_{c}"] = f1[..., i]
        out[f"IoU_{c}"] = iou[..., i]
        out[f"area_{c}"] = area[..., i]
        out[f"maparea_{c}"] = maparea[..., i]
    out["macroF1"] = f1.mean(axis=-1)
    out["mIoU"] = iou.mean(axis=-1)
    return out


def ratio_from_confusion(conf: np.ndarray, rp: RatioParams) -> np.ndarray:
    """Ratio parameters (..., P) from a (..., 6, 5) confusion: sum(A_y * C) / sum(A_x * C)."""
    y = np.einsum("...ij,pij->...p", conf, rp.ay)
    x = np.einsum("...ij,pij->...p", conf, rp.ax)
    return _div(y, x)
