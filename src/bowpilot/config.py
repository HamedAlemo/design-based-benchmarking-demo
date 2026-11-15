"""Load and validate every YAML file in config/, resolve the active extent, and expose a typed Config.

All tunable numbers (class codes, budgets, thresholds, seeds) come from here. Modules never hard-code them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
CONFIG_FILES = ["extent", "classes", "products", "frames", "arms", "montecarlo"]


class ConfigError(ValueError):
    """Raised when a configuration file violates a validation rule."""


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ConfigError(f"{path} does not contain a mapping")
    return data


@dataclass
class Config:
    """Typed view on the YAML configuration.

    Attributes hold the raw dictionaries; properties give derived, validated values.
    """

    extent_cfg: dict
    classes: dict
    products: dict
    frames: dict
    arms_cfg: dict
    montecarlo: dict
    extent: str
    root: Path = field(default=REPO_ROOT)

    # ------------------------------------------------------------------ paths
    @property
    def data_dir(self) -> Path:
        return self.root / "data" / self.extent

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def interim_dir(self) -> Path:
        return self.data_dir / "interim"

    @property
    def rasters_dir(self) -> Path:
        return self.interim_dir / "rasters"

    @property
    def cells_dir(self) -> Path:
        return self.interim_dir / "cells"

    @property
    def units_dir(self) -> Path:
        return self.interim_dir / "units"

    @property
    def results_dir(self) -> Path:
        return self.root / "results" / self.extent

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"

    # ------------------------------------------------------------------ grid / extent
    @property
    def crs(self) -> str:
        return self.extent_cfg["grid"]["crs"]

    @property
    def cell_size(self) -> int:
        return int(self.extent_cfg["grid"]["cell_size_m"])

    @property
    def bbox_lonlat(self) -> list[float] | None:
        return self.extent_cfg["extents"][self.extent]["bbox_lonlat"]

    @property
    def states(self) -> list[dict]:
        return self.extent_cfg["states"]

    # ------------------------------------------------------------------ models / classes
    @property
    def model_keys(self) -> list[str]:
        return [m["key"] for m in self.products["models"]]

    @property
    def model_short(self) -> dict[str, str]:
        return {m["key"]: m["short"] for m in self.products["models"]}

    @property
    def n_models(self) -> int:
        return len(self.model_keys)

    @property
    def pairs(self) -> list[tuple[int, int]]:
        """Model pairs in fixed order (0,1), (0,2), (1,2), ..."""
        k = self.n_models
        return [(a, b) for a in range(k) for b in range(a + 1, k)]

    @property
    def class_codes(self) -> list[int]:
        return sorted(int(c) for c in self.classes["harmonized"])

    @property
    def class_names(self) -> dict[int, str]:
        return {int(c): n for c, n in self.classes["harmonized"].items()}

    def product_model(self, key: str) -> dict:
        for m in self.products["models"]:
            if m["key"] == key:
                return m
        raise KeyError(key)

    def gee_project(self) -> str | None:
        return os.environ.get("GEE_PROJECT") or self.product_model("dynamic_world_2021").get("gee_project")

    # ------------------------------------------------------------------ frames
    @property
    def purity_thresholds(self) -> list[float]:
        return [float(t) for t in self.frames["chips"]["purity_thresholds"]]

    @property
    def chip_size(self) -> int:
        return int(self.frames["chips"]["size_cells"])

    # ------------------------------------------------------------------ arms
    @property
    def arms(self) -> dict[str, dict]:
        """Arm specs with dev overrides applied when the active extent is dev."""
        arms = {k: dict(v) for k, v in self.arms_cfg["arms"].items()}
        if self.extent == "dev":
            for name, override in (self.arms_cfg.get("dev_overrides") or {}).items():
                arms[name] = {**arms[name], **override}
        return arms

    def budgets(self, arm: str) -> list[int]:
        """Budget values for an arm; arms with `draws_from` inherit their source arm's budgets."""
        spec = self.arms[arm]
        if "budgets" not in spec and "draws_from" in spec:
            return self.budgets(spec["draws_from"])
        (vals,) = spec["budgets"].values()
        return list(vals)

    # ------------------------------------------------------------------ monte carlo
    @property
    def mc_profile(self) -> dict:
        return self.montecarlo["profiles"][self.extent]

    @property
    def base_seed(self) -> int:
        return int(self.montecarlo["base_seed"])

    @property
    def confidence_level(self) -> float:
        return float(self.montecarlo["confidence_level"])


def validate(cfg: Config) -> None:
    """Check the rules from M0 step 4. Raises ConfigError on the first violation."""
    if cfg.extent not in cfg.extent_cfg["extents"]:
        raise ConfigError(f"unknown extent {cfg.extent!r}")
    # crosswalks map into 0..5
    for product, table in cfg.classes["products"].items():
        for code, target in table.items():
            if target not in range(6):
                raise ConfigError(f"crosswalk {product}: {code} -> {target} not in 0..5")
    for name, target in cfg.classes["reference"]["name_to_harmonized"].items():
        if target not in range(1, 6):
            raise ConfigError(f"reference {name} -> {target} not in 1..5")
    for key in cfg.model_keys:
        if key not in cfg.classes["products"]:
            raise ConfigError(f"model {key} has no crosswalk")
    # purity thresholds
    for where, t in [("frames", cfg.frames["chips"]["purity_thresholds"])] + [
        (f"arms.{a}", s["purity_thresholds"]) for a, s in cfg.arms_cfg["arms"].items() if "purity_thresholds" in s
    ]:
        if list(t) != sorted(t) or not all(0.0 <= float(x) <= 1.0 for x in t):
            raise ConfigError(f"purity thresholds in {where} must be sorted in [0, 1]: {t}")
        if not set(float(x) for x in t) <= set(cfg.purity_thresholds):
            raise ConfigError(f"purity thresholds in {where} not all in frames.chips.purity_thresholds")
    # arms
    for extent in cfg.extent_cfg["extents"]:
        view = Config(**{**cfg.__dict__, "extent": extent})
        for name, spec in view.arms.items():
            if "draws_from" in spec and spec["draws_from"] not in view.arms:
                raise ConfigError(f"arm {name} draws from unknown arm {spec['draws_from']}")
            for b in view.budgets(name):
                if not (isinstance(b, int) and b > 0):
                    raise ConfigError(f"arm {name}: budget {b} is not a positive integer")
    # montecarlo profile
    if cfg.extent not in cfg.montecarlo["profiles"]:
        raise ConfigError(f"no montecarlo profile for extent {cfg.extent}")
    for k in ("replicates", "bootstrap_subset", "bootstrap_B"):
        v = cfg.mc_profile[k]
        if not (isinstance(v, int) and v > 0):
            raise ConfigError(f"montecarlo.{cfg.extent}.{k} must be a positive integer")
    if cfg.mc_profile["bootstrap_subset"] > cfg.mc_profile["replicates"]:
        raise ConfigError("bootstrap_subset exceeds replicates")


def load_config(extent: str | None = None, config_dir: Path = CONFIG_DIR, root: Path = REPO_ROOT) -> Config:
    """Load all YAML files, resolve the extent (argument, else `active` in extent.yaml) and validate."""
    raw: dict[str, Any] = {name: _load_yaml(config_dir / f"{name}.yaml") for name in CONFIG_FILES}
    cfg = Config(
        extent_cfg=raw["extent"],
        classes=raw["classes"],
        products=raw["products"],
        frames=raw["frames"],
        arms_cfg=raw["arms"],
        montecarlo=raw["montecarlo"],
        extent=extent or raw["extent"]["active"],
        root=root,
    )
    validate(cfg)
    return cfg
