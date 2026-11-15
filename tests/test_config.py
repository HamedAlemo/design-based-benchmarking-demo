"""Smoke tests for the configuration files. M0 extends these once config.py exists."""

from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parents[1] / "config"


def load(name: str) -> dict:
    with open(CONFIG / name) as f:
        return yaml.safe_load(f)


def test_all_configs_parse():
    for name in ["extent.yaml", "classes.yaml", "products.yaml", "frames.yaml", "arms.yaml", "montecarlo.yaml"]:
        assert isinstance(load(name), dict), name


def test_crosswalks_map_into_0_to_5():
    classes = load("classes.yaml")
    for product, table in classes["products"].items():
        for code, target in table.items():
            assert target in range(6), (product, code, target)
    for name, target in classes["reference"]["name_to_harmonized"].items():
        assert target in range(1, 6), (name, target)


def test_arms_reference_existing_arms():
    arms = load("arms.yaml")["arms"]
    for name, spec in arms.items():
        if "draws_from" in spec:
            assert spec["draws_from"] in arms, name


def test_purity_thresholds_sorted_in_unit_interval():
    t = load("frames.yaml")["chips"]["purity_thresholds"]
    assert t == sorted(t) and all(0.0 <= x <= 1.0 for x in t)
