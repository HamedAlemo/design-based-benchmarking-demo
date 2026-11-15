"""M3 items 4 (R survey cross-check) and the speed acceptance check."""

import shutil
import time

import numpy as np
import pytest

from bowpilot.contracts import ClusterSample, ElementSample, StratumInfo
from bowpilot.estimation.estimate import design_cluster, design_element

PAIRS = [(0, 1), (0, 2), (1, 2)]


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="R not installed")
def test_r_survey_agreement():
    from bowpilot.validation.r_check import run_r_check

    r = run_r_check()
    assert (r["rel_diff_estimate"] < 1e-6).all(), r.to_string()
    assert (r["rel_diff_se"] < 1e-6).all(), r.to_string()


def _median_ms(fn, reps=50):
    fn()
    t = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        t.append(time.perf_counter() - t0)
    return 1000 * float(np.median(t))


def test_speed_element_and_cluster():
    """One full estimate set (3 models, all parameters, linearized SE, pairwise OA) < 20 ms at n = 2000 and at
    200 PSUs."""
    rng = np.random.default_rng(0)
    n, H = 2000, 11  # noqa: N806
    st = np.repeat(np.arange(H), n // H + 1)[:n]
    strata = [StratumInfo(h, 100_000, int((st == h).sum())) for h in range(H)]
    ref = rng.integers(1, 6, n).astype(np.uint8)
    maps = np.where(rng.random((n, 3)) < 0.8, ref[:, None], rng.integers(0, 6, (n, 3))).astype(np.uint8)
    es = ElementSample(np.arange(n), np.array([s.sampled_units / 1e5 for s in strata])[st], st, strata, ref, maps)
    t_el = _median_ms(lambda: design_element(es, PAIRS))
    m = 200
    conf = rng.integers(0, 500, (m, 3, 6, 5))
    conf[:, 1:] = conf[:, :1]
    cs = ClusterSample(np.arange(m), np.full(m, 0.1), np.repeat([0, 1], 100),
                       [StratumInfo(0, 1000, 100), StratumInfo(1, 1000, 100)], conf, rng.integers(0, 50, (m, 3, 2)))
    t_cl = _median_ms(lambda: design_cluster(cs, PAIRS))
    print(f"element {t_el:.2f} ms, cluster {t_cl:.2f} ms")
    assert t_el < 20 and t_cl < 20
