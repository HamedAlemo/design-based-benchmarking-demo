"""M4 sampler tests: allocation unit tests and the full validation on the tiny synthetic extent."""

import numpy as np
import pytest

from bowpilot.sampling.allocation import allocate, largest_remainder
from bowpilot.sampling.cluster import tag_quotas


def test_largest_remainder():
    assert largest_remainder(10, np.array([1, 1, 1])).tolist() == [4, 3, 3]
    assert largest_remainder(7, np.array([0.5, 0.25, 0.25])).sum() == 7


def test_allocate_sums_minimum_and_caps():
    N_h = np.array([1000, 5000, 3, 200_000, 40])  # noqa: N806
    n_h = allocate(500, N_h, 50, N_h.astype(float))
    assert n_h.sum() == 500
    assert n_h[2] == 3                         # capped at N_h below m_min
    assert (n_h[[0, 1]] >= 50).all() and n_h[4] == 40   # stratum 4 capped at its 40 cells
    assert (n_h <= N_h).all()


def test_allocate_edge_cases():
    # stratum smaller than m_min, excess redistributed; minimum 2 where N_h >= 2
    n_h = allocate(20, np.array([1, 2, 1000]), 50, np.array([1.0, 1.0, 1.0]))
    assert n_h.tolist()[:2] == [1, 2] and n_h.sum() == 20
    with pytest.raises(ValueError):
        allocate(10, np.array([3, 3]), 2, np.ones(2))


def test_tag_quotas_redistribution():
    q = tag_quotas(100, {4: 5, 1: 10, 5: 1000, 2: 1000, 3: 1000}, [4, 1, 5, 2, 3])
    assert q[4] == 5 and q[1] == 10 and sum(q.values()) == 100
    assert sorted([q[5], q[2], q[3]]) == [28, 28, 29]


@pytest.fixture(scope="module")
def m4(tiny_population):
    from bowpilot.validation.m4 import run_m4

    cfg, _ = tiny_population
    return run_m4(cfg, uniform_draws=4000, b2_draws=1000)


def test_sizes_and_weights(m4):
    for arm, v in m4["sizes_weights"].items():
        assert all(v.values()), (arm, v)
    assert m4["b2_total"]["pass"], m4["b2_total"]


def test_uniform_selection(m4):
    for arm, v in m4["cluster_uniform"].items():
        assert v["pass"], (arm, v)
    assert m4["cluster_uniform"]["A1"]["incomplete_ever_selected"] == 0
    for arm, v in m4["element_uniform"].items():
        assert v["pass"], (arm, v)


def test_pairing_and_determinism(m4):
    assert all(m4["pairing_determinism"].values()), m4["pairing_determinism"]
