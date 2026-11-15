"""Arm registry: arm name to sampler, estimator, budgets, purity thresholds and draws_from (M4 item 4).

A `Context` opens the cell-table memmaps, cached stratum indices and per-PSU unit arrays once. `draw(arm, budget,
rng)` returns a `Draw`; `evaluate(draw)` returns (arm label, tau, EstimateSet) for the drawing arm and every arm that
reuses its draw (A0 -> A0w; A1 -> B1 at each tau; D -> E). F returns one EstimateSet per model, each from that
model's own sample, and only that model's estimates are kept.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from bowpilot.config import Config
from bowpilot.contracts import ClusterSample, ElementSample, StratumInfo
from bowpilot.estimation.estimate import EstimateSet, design_cluster, design_element, naive_cluster, naive_element
from bowpilot.sampling.allocation import allocate, neyman_weights_D
from bowpilot.sampling.cluster import cluster_sample, equal_per_tag, srs_tiles_per_state
from bowpilot.sampling.element import StratumIndex, build_stratum_index, srs_cells, stratified_cells

DRAWING_ARMS = ["A0", "A1", "B2", "C", "D", "D2", "F"]          # arms that draw; the rest reuse a draw
REUSING = {"A0w": "A0", "B1": "A1", "E": "D"}


def _min_base(spec: dict) -> int:
    """Parse 'min(B, floor(n / (2 * H)))' -> B."""
    s = spec["allocation"]["min_per_stratum"]
    return int(s.split("(")[1].split(",")[0])


@dataclass
class Draw:
    arm: str
    budget: int
    element: ElementSample | None = None
    cluster_psu: tuple | None = None                  # (psu, pi, stratum, StratumInfo list)
    per_model: list[ElementSample] = field(default_factory=list)


class Context:
    """Read-only handles for one extent. Never reads truth."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        cd, ud = cfg.cells_dir, cfg.units_dir
        self.ref = np.load(cd / "ref.npy", mmap_mode="r")
        self.maps = [np.load(cd / f"map_{k}.npy", mmap_mode="r") for k in cfg.model_keys]
        self.state = np.load(cd / "state.npy", mmap_mode="r")
        self.N = len(self.ref)
        self.pairs = cfg.pairs
        idx_dir = cfg.interim_dir / "strata_idx"
        self.si: dict[str, StratumIndex] = {}
        for name in ["strat_D", "strat_D2"] + [f"strat_F_{k}" for k in cfg.model_keys]:
            self.si[name] = build_stratum_index(np.load(cd / f"{name}.npy", mmap_mode="r"),
                                                idx_dir / f"{name}.npz")
        fd = cfg.interim_dir / "frames"
        self.D_lookup = pd.read_csv(fd / "strata_D.csv").set_index("stratum_id")
        tm = pd.read_parquet(ud / "tiles_meta.parquet").sort_values("tile_id")
        self.tiles_meta = tm
        self.tiles_conf = np.load(ud / "tiles_conf.npy", mmap_mode="r")
        self.tiles_disc = np.load(ud / "tiles_disc.npy", mmap_mode="r")
        cm = pd.read_parquet(ud / "chips_meta.parquet").sort_values("chip_id")
        self.chips_meta = cm
        self.chip_tag = cm["tag"].to_numpy()
        self.chip_complete = cm["complete"].to_numpy()
        self.chips_conf = np.load(ud / "chips_conf.npy", mmap_mode="r")
        self.chips_disc = np.load(ud / "chips_disc.npy", mmap_mode="r")
        self.rarity = json.loads((fd / "rarity.json").read_text())["rarity_order"]
        self.taus = cfg.purity_thresholds
        # known map proportions W_i^(k) (auxiliary map information, not reference truth)
        self.map_props = np.stack([np.bincount(np.asarray(m), minlength=6) / self.N for m in self.maps])
        self._alloc: dict = {}

    # ------------------------------------------------------------------ allocations
    def allocation(self, arm: str, n: int, model: str | None = None) -> np.ndarray:
        key = (arm, n, model)
        if key not in self._alloc:
            spec = self.cfg.arms[arm]
            if arm == "D":
                si = self.si["strat_D"]
                levels = [self.D_lookup.loc[i, "level"] for i in si.ids]
                w = neyman_weights_D(si.N_h, levels, spec["allocation"]["assumed_error_rate"])
            elif arm == "D2":
                si = self.si["strat_D2"]
                w = si.N_h.astype(float)
            elif arm == "F":
                si = self.si[f"strat_F_{model}"]
                w = si.N_h.astype(float)
            else:
                raise KeyError(arm)
            self._alloc[key] = allocate(n, si.N_h, _min_base(spec), w)
        return self._alloc[key]

    # ------------------------------------------------------------------ draws
    def draw(self, arm: str, budget: int, rng: np.random.Generator) -> Draw:
        d = Draw(arm, budget)
        if arm == "A0":
            d.cluster_psu = srs_tiles_per_state(rng, self.tiles_meta["stratum"].to_numpy(), budget)
        elif arm == "A1":
            d.cluster_psu = equal_per_tag(rng, self.chip_tag, self.chip_complete, budget, self.rarity)
        elif arm == "B2":
            d.cluster_psu = equal_per_tag(rng, self.chip_tag, np.ones_like(self.chip_complete), budget, self.rarity)
        elif arm == "C":
            d.element = srs_cells(rng, self.N, budget, self.ref, self.maps)
        elif arm in ("D", "D2"):
            d.element = stratified_cells(rng, self.si[f"strat_{arm}"], self.allocation(arm, budget), self.ref,
                                         self.maps)
        elif arm == "F":
            d.per_model = [stratified_cells(rng, self.si[f"strat_F_{k}"], self.allocation("F", budget, k), self.ref,
                                            self.maps) for k in self.cfg.model_keys]
        else:
            raise KeyError(f"{arm} does not draw; it reuses {REUSING.get(arm)}")
        return d

    def tile_sample(self, d: Draw) -> ClusterSample:
        return cluster_sample(*d.cluster_psu, self.tiles_conf, self.tiles_disc)

    def chip_sample(self, d: Draw, tau: float) -> ClusterSample:
        t = self.taus.index(tau)
        psu = d.cluster_psu[0]
        o = np.argsort(psu)
        p = psu[o]
        return ClusterSample(p.astype(np.int64), d.cluster_psu[1][o], d.cluster_psu[2][o], d.cluster_psu[3],
                             np.asarray(self.chips_conf[p, t]), np.asarray(self.chips_disc[p, t]), tau)

    # ------------------------------------------------------------------ evaluation
    def evaluate(self, d: Draw, boot: tuple | None = None) -> list[tuple[str, float, EstimateSet]]:
        """(arm label, tau, EstimateSet) for the drawing arm and every arm reusing the draw."""
        p = self.pairs
        out: list[tuple[str, float, EstimateSet]] = []
        if d.arm == "A0":
            s = self.tile_sample(d)
            out += [("A0", 0.0, naive_cluster(s, p)), ("A0w", 0.0, design_cluster(s, p, boot))]
        elif d.arm == "A1":
            for tau in self.cfg.arms["A1"]["purity_thresholds"]:
                out.append(("A1", float(tau), naive_cluster(self.chip_sample(d, float(tau)), p)))
            for tau in self.cfg.arms["B1"]["purity_thresholds"]:
                out.append(("B1", float(tau), design_cluster(self.chip_sample(d, float(tau)), p, boot)))
        elif d.arm == "B2":
            out.append(("B2", 0.0, design_cluster(self.chip_sample(d, 0.0), p, boot)))
        elif d.arm in ("C", "D2"):
            out.append((d.arm, 0.0, design_element(d.element, p, boot)))
        elif d.arm == "D":
            out += [("D", 0.0, design_element(d.element, p, boot)), ("E", 0.0, naive_element(d.element, p))]
        elif d.arm == "F":
            for s in d.per_model:
                out.append(("F", 0.0, design_element(s, [], boot)))
        return out

    # ------------------------------------------------------------------ the real CVPR split
    def actual_cvpr_test_split(self, n_per_state: int = 20) -> ClusterSample:
        """Fixed ClusterSample of matched CVPR test tiles; pi = 20 / M_s is for documentation only (the real split
        was drawn from the CVPR frame, not ours)."""
        tm = self.tiles_meta
        sel = tm[tm["cvpr_split"] == "test"]
        st = sel["stratum"].to_numpy().astype(np.int32)
        info, pis = [], np.empty(len(sel))
        for s in np.unique(st):
            m_s = int((tm["stratum"] == s).sum())
            k = int((st == s).sum())
            info.append(StratumInfo(int(s), m_s, k))
            pis[st == s] = min(1.0, n_per_state / m_s)
        psu = sel["tile_id"].to_numpy()
        return cluster_sample(psu, pis, st, info, self.tiles_conf, self.tiles_disc)
