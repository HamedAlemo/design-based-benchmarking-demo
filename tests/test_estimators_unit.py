"""Hand-worked estimator tests (M3 validation item 1). Expected values are derived by hand in each docstring."""

import numpy as np
import pytest

from bowpilot.contracts import ClusterSample, ElementSample, StratumInfo
from bowpilot.estimation.estimate import design_cluster, design_element, naive_cluster
from bowpilot.estimation.model_assisted import poststratified_area
from bowpilot.estimation.naive import binomial_se, mcnemar
from bowpilot.estimation.params import metrics_from_confusion
from bowpilot.estimation.variance import var_ratio_element


def element_sample() -> ElementSample:
    """Two strata, 8 cells, one model. (map, ref) pairs:

    stratum 1 (N_1 = 100, n_1 = 4, w = 25):   (1,1) (2,2) (3,2) (3,3)
    stratum 2 (N_2 = 50,  n_2 = 4, w = 12.5): (2,2) (2,3) (5,5) (1,1)
    """
    maps = np.array([[1], [2], [3], [3], [2], [2], [5], [1]], dtype=np.uint8)
    ref = np.array([1, 2, 2, 3, 2, 3, 5, 1], dtype=np.uint8)
    stratum = np.array([1, 1, 1, 1, 2, 2, 2, 2], dtype=np.int32)
    pi = np.where(stratum == 1, 4 / 100, 4 / 50)
    return ElementSample(np.arange(8), pi, stratum, [StratumInfo(1, 100, 4), StratumInfo(2, 50, 4)], ref, maps)


def test_element_point_estimates():
    """OA = (25*3 + 12.5*3) / 150 = 0.75.
    UA_2: Y = 25 + 12.5 = 37.5 (cells (2,2) in both strata), X = 25 + 2*12.5 = 50 -> 0.75.
    PA_2: Y = 37.5, X = 2*25 + 12.5 = 62.5 -> 0.6.
    area_2: Y = 62.5, X = 150 -> 0.416667.  area_3: Y = 25 + 12.5 = 37.5 -> 0.25.
    F1_2 = 2 * 37.5 / (50 + 62.5) = 0.666667.
    """
    es = design_element(element_sample(), pairs=[])
    assert es.est["OA"][0] == pytest.approx(0.75)
    assert es.est["UA_2"][0] == pytest.approx(0.75)
    assert es.est["PA_2"][0] == pytest.approx(0.6)
    assert es.est["area_2"][0] == pytest.approx(62.5 / 150)
    assert es.est["area_3"][0] == pytest.approx(0.25)
    assert es.est["F1_2"][0] == pytest.approx(2 / 3)


def test_element_variance_oa_and_ua():
    """OA: z = (y - 0.75) / 150. In both strata y - 0.75 has three 0.25s and one -0.75: s2 = 0.75 / 3 = 0.25.
    V = [100^2 (1 - 0.04) 0.25 / 4 + 50^2 (1 - 0.08) 0.25 / 4] / 150^2 = (600 + 143.75) / 22500 = 0.0330556.

    UA_2: R = 0.75, X_hat = 50, e = y - R x.
    stratum 1: e = (0, 0.25, 0, 0): mean 0.0625, ss = 3 * 0.0625^2 + 0.1875^2 = 0.046875, s2 = 0.015625.
    stratum 2: e = (0.25, -0.75, 0, 0): mean -0.125, ss = 0.5625, s2 = 0.1875.
    V = [10000 * 0.96 * 0.015625 / 4 + 2500 * 0.92 * 0.1875 / 4] / 50^2 = (37.5 + 107.8125) / 2500 = 0.058125.
    """
    es = design_element(element_sample(), pairs=[])
    assert es.se["OA"][0] ** 2 == pytest.approx(743.75 / 22500)
    assert es.se["UA_2"][0] ** 2 == pytest.approx(0.058125)


def test_element_strata_check():
    s = element_sample()
    with pytest.raises(ValueError):
        var_ratio_element(np.ones((8, 1)), np.ones((8, 1)), 1 / s.pi, s.stratum,
                          [StratumInfo(1, 100, 5), StratumInfo(2, 50, 3)])
    # single-unit stratum that is not a census
    with pytest.raises(ValueError):
        var_ratio_element(np.ones((2, 1)), np.ones((2, 1)), np.array([10.0, 10.0]), np.array([1, 2]),
                          [StratumInfo(1, 10, 1), StratumInfo(2, 10, 1)])


def cluster_sample() -> ClusterSample:
    """Five PSUs, one model, all cells reference class 1. (correct, cells) per PSU:

    stratum A (M = 10, m = 3, w = 10/3): (8, 10) (5, 10) (9, 12)
    stratum B (M = 4,  m = 2, w = 2):    (3, 5)  (4, 4)
    Correct cells are mapped class 1, wrong cells class 2.
    """
    correct = np.array([8, 5, 9, 3, 4])
    cells = np.array([10, 10, 12, 5, 4])
    conf = np.zeros((5, 1, 6, 5), dtype=np.int64)
    conf[:, 0, 1, 0] = correct
    conf[:, 0, 2, 0] = cells - correct
    stratum = np.array([0, 0, 0, 1, 1])
    pi = np.where(stratum == 0, 3 / 10, 2 / 4)
    return ClusterSample(np.arange(5), pi, stratum, [StratumInfo(0, 10, 3), StratumInfo(1, 4, 2)], conf,
                         np.zeros((5, 0, 2), dtype=np.int64))


def test_cluster_oa_and_variance():
    """Y = 10/3 * 22 + 2 * 7 = 262/3, X = 10/3 * 32 + 2 * 9 = 374/3, R = 131/187 = 0.7005348.
    t_i * X_hat = Y_i - R X_i. Stratum A: (0.994652, -2.005348, 0.593583), s2 = 2.652550.
    Stratum B: (-0.502674, 1.197861), s2 = 1.445909.
    V = [10^2 (1 - 3/10) 2.652550 / 3 + 4^2 (1 - 2/4) 1.445909 / 2] / (374/3)^2 = 0.00435449.
    """
    es = design_cluster(cluster_sample(), pairs=[])
    assert es.est["OA"][0] == pytest.approx(131 / 187)
    assert es.se["OA"][0] ** 2 == pytest.approx(0.004354486163521337, rel=1e-9)
    # PA_1 equals OA (all reference is class 1); UA_1 = 1 (every cell mapped 1 is right); UA_3 undefined
    assert es.est["PA_1"][0] == pytest.approx(131 / 187)
    assert es.est["UA_1"][0] == pytest.approx(1.0)
    assert np.isnan(es.est["UA_3"][0])


def test_naive_pooled_cluster():
    """Pooled: 29 correct of 41 cells -> OA = 0.707317, binomial SE sqrt(p (1 - p) / 41)."""
    es = naive_cluster(cluster_sample(), pairs=[])
    p = 29 / 41
    assert es.est["OA"][0] == pytest.approx(p)
    assert es.se["OA"][0] == pytest.approx(np.sqrt(p * (1 - p) / 41))


def test_metrics_nan_on_zero_denominator():
    conf = np.zeros((6, 5))
    conf[1, 0] = 10
    m = metrics_from_confusion(conf)
    assert m["OA"] == 1.0
    assert np.isnan(m["UA_2"]) and np.isnan(m["PA_2"]) and np.isnan(m["F1_2"]) and np.isnan(m["macroF1"])
    assert m["area_2"] == 0.0


def test_naive_helpers():
    assert mcnemar(np.array(9.0), np.array(4.0)) == pytest.approx(5 / np.sqrt(13))
    assert mcnemar(np.array(0.0), np.array(0.0)) == 0.0
    assert np.isnan(binomial_se(np.array(0.5), np.array(0)))


def test_poststratified_area_hand():
    """One stratum, N = 100, n = 4 (w = 25). (map, ref): (1,1) (1,2) (2,2) (2,2). Known map proportions W_1 = 0.3,
    W_2 = 0.7, others 0. p(r=2 | m=1) = 0.5, p(r=2 | m=2) = 1 -> area_2 = 0.3 * 0.5 + 0.7 * 1 = 0.85,
    area_1 = 0.3 * 0.5 = 0.15.
    SE for area_2: z_u = sum_i W_i (y_iu - R_i x_iu) / X_i, X_1 = X_2 = 50.
    z = (0.3 (0 - 0.5) / 50, 0.3 (1 - 0.5) / 50, 0, 0) = (-0.003, 0.003, 0, 0): mean 0, s2 = 1.8e-5 / 3 = 6e-6.
    V = 100^2 (1 - 0.04) 6e-6 / 4 = 0.0144, SE = 0.12.
    """
    W = np.array([0, 0.3, 0.7, 0, 0, 0])  # noqa: N806
    est, se = poststratified_area(np.array([1, 1, 2, 2]), np.array([1, 2, 2, 2]), np.full(4, 25.0),
                                  np.zeros(4, dtype=int), [StratumInfo(0, 100, 4)], W)
    assert est[1] == pytest.approx(0.85)
    assert est[0] == pytest.approx(0.15)
    assert se[1] == pytest.approx(0.12)
