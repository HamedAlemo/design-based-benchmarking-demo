"""M2 driver: cell table, frames, strata, per-unit arrays and truth; acceptance checks into m2_summary.json."""

from __future__ import annotations

import json
import logging
import time

import numpy as np

from bowpilot.config import Config
from bowpilot.grid import Grid
from bowpilot.population import cell_table, frames, truth, units

log = logging.getLogger(__name__)


def cell_table_checks(cfg: Config) -> dict:
    n = json.loads((cfg.cells_dir / "meta.json").read_text())["N"]
    lengths = {p.stem: int(np.load(p, mmap_mode="r").shape[0]) for p in cfg.cells_dir.glob("*.npy")}
    ref = cell_table.load(cfg, "ref")
    maps_max = {k: int(np.max(cell_table.load(cfg, f"map_{k}"))) for k in cfg.model_keys}
    return {"all_length_N": all(v == n for v in lengths.values()), "lengths": lengths,
            "ref_zero": int((ref == 0).sum()), "ref_max": int(ref.max()), "map_max": maps_max,
            "pass": all(v == n for v in lengths.values()) and int((ref == 0).sum()) == 0
            and all(v <= 5 for v in maps_max.values())}


def run_population(cfg: Config) -> dict:
    missing = [k for k in cfg.model_keys if not (cfg.rasters_dir / f"map_{k}.tif").exists()]
    if missing:
        raise RuntimeError(f"M2 needs every model map; missing {missing} (see reports/M1.md)")
    grid = Grid.from_json(cfg.interim_dir / "grid.json")
    res: dict = {}
    steps = [("cell_table", lambda: cell_table.build_cell_table(cfg, grid)),
             ("cell_table_checks", lambda: cell_table_checks(cfg)),
             ("tiles", lambda: frames.build_tiles(cfg)),
             ("chips", lambda: frames.build_chips(cfg, grid)),
             ("strata_D", lambda: frames.strata_D(cfg)),
             ("strata_D2", lambda: frames.strata_D2(cfg)),
             ("strata_F", lambda: frames.strata_F(cfg)),
             ("units", lambda: units.build_units(cfg)),
             ("truth", lambda: truth.compute_truth(cfg, grid))]
    for name, fn in steps:
        t0 = time.time()
        log.info("M2 step %s", name)
        res[name] = fn()
        res[name + "_seconds"] = round(time.time() - t0, 1)
        (cfg.interim_dir / "m2_summary.json").write_text(json.dumps(res, indent=2, default=str))
    return res
