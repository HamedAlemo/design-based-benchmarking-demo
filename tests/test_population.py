"""M2 end-to-end checks on the tiny synthetic extent (acceptance logic of docs/milestones/M2_population.md)."""

import numpy as np
import pandas as pd

from bowpilot.population.cell_table import load


def test_cell_table(tiny_population):
    cfg, res = tiny_population
    assert res["cell_table_checks"]["pass"]
    n = res["cell_table"]["N"]
    assert n == 1068 * 1260 - 10 * 300
    row, col = load(cfg, "row"), load(cfg, "col")
    flat = row.astype(np.int64) * 1280 + col
    assert np.all(np.diff(flat) > 0)        # row-major order


def test_tiles_and_chips(tiny_population):
    cfg, res = tiny_population
    n = res["cell_table"]["N"]
    assert res["tiles"]["sum_n_cells"] == n
    assert res["chips"]["sum_n_cells"] == n
    chips = pd.read_parquet(cfg.interim_dir / "frames" / "chips_frame.parquet")
    assert chips["complete"].sum() == res["chips"]["complete_chips"] > 0
    assert set(chips["tag"]) <= {1, 2, 3, 4, 5}


def test_cvpr_match(tiny_population):
    _, res = tiny_population
    assert res["tiles"]["cvpr"]["matched"] == 1
    assert res["tiles"]["cvpr"]["iou_min"] >= 0.8


def test_strata_sum_to_n(tiny_population):
    _, res = tiny_population
    n = res["cell_table"]["N"]
    assert res["strata_D"]["sum_N_h"] == n
    assert res["strata_D2"]["sum_N_h"] == n
    assert all(v["sum_N_h"] == n for v in res["strata_F"].values())


def test_unit_identities_and_truth_crosscheck(tiny_population):
    _, res = tiny_population
    assert all(res["truth"]["unit_identities"].values()), res["truth"]["unit_identities"]
    assert res["truth"]["cross_check_identical"]
