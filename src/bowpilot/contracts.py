"""Data contracts shared by every module.

These dataclasses are the interface between samplers (M4), estimators (M3) and the Monte Carlo driver (M5).
Keep them stable. If a field must change, record it in docs/DECISIONS.md and update all call sites and tests.

Conventions
-----------
- Class codes: reference classes 1..5 (config/classes.yaml `harmonized`); model maps 0..5, where 0 = no prediction.
- K = number of models, in the order of config/products.yaml `models`.
- Element designs: the sampling unit is one 10 m cell. Cluster designs: the sampling unit (PSU) is a tile or chip and
  every scored cell inside a selected PSU is observed (one-stage cluster sampling).
- Weights are design weights w = 1 / pi. For cluster designs pi is the PSU inclusion probability, shared by its cells.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

N_REF_CLASSES = 5          # reference classes 1..5
N_MAP_CLASSES = 6          # model classes 0..5 (0 = no prediction)


class DesignKind(StrEnum):
    ELEMENT = "element"    # cells sampled individually (C, D, D2, E, F)
    CLUSTER = "cluster"    # one-stage stratified cluster sample of tiles or chips (A0, A0w, A1, B1, B2)


class EstimatorKind(StrEnum):
    DESIGN_ELEMENT = "design_element"        # weighted ratios, stratified element linearization variance
    DESIGN_CLUSTER = "design_cluster"        # weighted ratios, stratified one-stage cluster linearization variance
    NAIVE_POOLED = "naive_pooled"            # unweighted pooled cells, binomial SE, McNemar pairs (A0, A1)
    NAIVE_UNWEIGHTED = "naive_unweighted"    # element sample analysed with equal weights (E)


@dataclass(frozen=True)
class StratumInfo:
    """Population and sample counts for one stratum.

    For element designs N_h / n_h count cells. For cluster designs they count PSUs (M_h / m_h in PROTOCOL.md).
    """

    stratum_id: int
    population_units: int      # N_h (cells) or M_h (PSUs)
    sampled_units: int         # n_h or m_h


@dataclass
class ElementSample:
    """A sample of individual cells.

    Attributes
    ----------
    cell_index : (n,) int64, positions in the cell table (data/interim/cells/*.npy).
    pi : (n,) float64, first-order inclusion probability of each cell. Must be > 0.
    stratum : (n,) int32, stratum id per cell (0 for unstratified designs).
    strata : list of StratumInfo, one per stratum, including strata with zero sampled units if any.
    ref : (n,) uint8, reference class 1..5, gathered from the cell table.
    maps : (n, K) uint8, model classes 0..5, gathered from the cell table.
    """

    cell_index: np.ndarray
    pi: np.ndarray
    stratum: np.ndarray
    strata: list[StratumInfo]
    ref: np.ndarray
    maps: np.ndarray


@dataclass
class ClusterSample:
    """A one-stage stratified cluster sample of PSUs (tiles or chips).

    Per-PSU sufficient statistics come from the precomputed unit arrays (M2), so no cell-level data is needed.

    Attributes
    ----------
    psu_index : (m,) int64, ids of selected PSUs in the frame.
    pi : (m,) float64, PSU inclusion probability (m_h / M_h for SRS within stratum h).
    stratum : (m,) int32, stratum of each selected PSU (state for tiles, rare-class tag for chips).
    strata : list of StratumInfo.
    confusion : (m, K, 6, 5) int64, per-PSU counts of (map class 0..5, ref class 1..5) over scored cells.
    discordant : (m, P, 2) int64, per-PSU McNemar counts for each model pair p = (k, l):
                 [:, p, 0] = cells where k correct and l wrong; [:, p, 1] = l correct and k wrong.
    purity_threshold : float, purity filter applied when scoring cells (0.0 = none).
    """

    psu_index: np.ndarray
    pi: np.ndarray
    stratum: np.ndarray
    strata: list[StratumInfo]
    confusion: np.ndarray
    discordant: np.ndarray
    purity_threshold: float = 0.0


@dataclass
class Estimate:
    """One parameter estimate for one model (or one model pair) from one replicate."""

    arm: str
    budget: int
    replicate: int
    seed: int
    model: str                 # model key, or "k|l" for pairwise differences
    parameter: str             # e.g. "OA", "UA_3", "F1_4", "macroF1", "area_2", "diff_OA"
    estimate: float
    se: float | None           # None when the arm has no SE for this parameter
    ci_low: float | None
    ci_high: float | None
    n_units: int               # cells (element) or PSUs (cluster)
    n_cells_scored: int
    extra: dict = field(default_factory=dict)   # e.g. {"purity_threshold": 0.9, "mcnemar_z": 2.3}
