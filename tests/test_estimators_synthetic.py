"""Synthetic-population estimator validation (M3 validation items 2 and 5). 20,000 draws per design and size.

Pass conditions (docs/milestones/M3_estimators.md, as amended by DECISIONS.md entry 22, approved by the PI):
- |mean estimate - truth - predicted second-order ratio bias| <= z_crit MCSE for OA, UA_c, PA_c and area_c, where
  z_crit is the Bonferroni limit at familywise alpha 0.01 over all bias cells tested (DECISIONS.md entry 23)
- |mean estimate - truth| <= 0.002 (materiality)
- mean(V_hat) / empirical variance in [0.9, 1.1] for OA at the larger sample size
- OA coverage in [0.93, 0.97] at the larger sample size (the smaller size is reported, not asserted)
- the naive pooled SE under-covers in the cluster case (documents that the test can detect it)
"""

import numpy as np
import pytest
from scipy.stats import norm

from bowpilot.estimation.bootstrap import bootstrap_confusions, bootstrap_se, raowu_weights
from bowpilot.estimation.estimate import design_cluster
from bowpilot.validation.synthetic import cluster_draw, cluster_population, element_population, run_cluster, run_element

DRAWS = 20_000
ELEMENT_SIZES = (500, 2000)
CLUSTER_SIZES = (40, 80)


@pytest.fixture(scope="module")
def element_results():
    pop = element_population()
    return {n: run_element(pop, n, DRAWS, seed=100 + n) for n in ELEMENT_SIZES}


@pytest.fixture(scope="module")
def cluster_results():
    pop = cluster_population()
    return {m: run_cluster(pop, m, DRAWS, seed=200 + m) for m in CLUSTER_SIZES}


FAMILY_ALPHA = 0.01


@pytest.fixture(scope="module")
def z_crit(element_results, cluster_results):
    n_cells = sum(len(d) for d in element_results.values()) + sum(len(d[0]) for d in cluster_results.values())
    return float(norm.ppf(1 - FAMILY_ALPHA / (2 * n_cells)))


def _check_bias(df, z):
    cols = ["design", "n", "model", "parameter", "R_def", "bias", "pred_bias", "mcse", "resid_mcse"]
    bad = df[(df["resid_mcse"].abs() > z) | (df["bias"].abs() > 0.002)]
    assert bad.empty, bad[cols].to_string()


@pytest.mark.parametrize("n", ELEMENT_SIZES)
def test_element_unbiased(element_results, z_crit, n):
    _check_bias(element_results[n], z_crit)


@pytest.mark.parametrize("m", CLUSTER_SIZES)
def test_cluster_unbiased(cluster_results, z_crit, m):
    _check_bias(cluster_results[m][0], z_crit)


def test_element_variance_ratio_and_coverage(element_results):
    oa = element_results[max(ELEMENT_SIZES)].query("parameter == 'OA'")
    assert oa["var_ratio"].between(0.9, 1.1).all(), oa.to_string()
    assert oa["coverage"].between(0.93, 0.97).all(), oa.to_string()


def test_cluster_variance_ratio_and_coverage(cluster_results):
    oa = cluster_results[max(CLUSTER_SIZES)][0].query("parameter == 'OA'")
    assert oa["var_ratio"].between(0.9, 1.1).all(), oa.to_string()
    assert oa["coverage"].between(0.93, 0.97).all(), oa.to_string()


def test_naive_pooled_undercovers_in_cluster_case(cluster_results):
    for m in CLUSTER_SIZES:
        oa = cluster_results[m][1].query("parameter == 'OA'")
        assert (oa["coverage"] < 0.90).all(), oa.to_string()


def test_bootstrap_matches_linearization():
    """On 200 synthetic cluster draws the mean Rao-Wu bootstrap SE of OA is within 10% of the linearized SE."""
    pop = cluster_population()
    rng = np.random.default_rng(5)
    m_h = np.array([40, 40])
    lin, boot = [], []
    for _ in range(200):
        s = cluster_draw(rng, pop, m_h)
        es = design_cluster(s, pairs=[])
        bw = raowu_weights(rng, 1 / s.pi, s.stratum, s.strata, 200)
        bse = bootstrap_se(bootstrap_confusions(s.confusion, bw), ["OA"])["OA"]
        lin.append(es.se["OA"])
        boot.append(bse)
    ratio = np.mean(boot, axis=0) / np.mean(lin, axis=0)
    assert np.all(np.abs(ratio - 1) < 0.10), ratio
