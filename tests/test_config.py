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


# ---------------------------------------------------------------- config.py (M0)
import copy  # noqa: E402

import pytest  # noqa: E402

from bowpilot.config import Config, ConfigError, load_config, validate  # noqa: E402


def test_load_config_both_extents():
    for extent in ("dev", "full"):
        cfg = load_config(extent)
        assert cfg.extent == extent
        assert cfg.n_models == 3
        assert cfg.pairs == [(0, 1), (0, 2), (1, 2)]
        assert cfg.class_codes == [1, 2, 3, 4, 5]


def test_dev_override_and_inherited_budgets():
    dev, full = load_config("dev"), load_config("full")
    assert dev.budgets("A0") == [2, 3, 5]
    assert full.budgets("A0") == [5, 10, 20]
    assert full.budgets("A0w") == full.budgets("A0")
    assert full.budgets("E") == full.budgets("D") == [500, 1000, 2000]


def _mutated(mutate) -> Config:
    cfg = load_config("dev")
    new = Config(**{k: copy.deepcopy(v) for k, v in cfg.__dict__.items()})
    mutate(new)
    return new


@pytest.mark.parametrize("mutate", [
    lambda c: c.arms_cfg["arms"]["C"]["budgets"].update(n=[500, -1]),
    lambda c: c.arms_cfg["arms"]["C"]["budgets"].update(n=[500.5]),
    lambda c: c.arms_cfg["arms"]["E"].update(draws_from="Z"),
    lambda c: c.frames["chips"].update(purity_thresholds=[0.9, 0.75]),
    lambda c: c.frames["chips"].update(purity_thresholds=[0.0, 1.5]),
    lambda c: c.classes["products"]["worldcover_2021"].update({10: 7}),
    lambda c: c.montecarlo["profiles"].pop("dev"),
])
def test_validation_rejects_bad_config(mutate):
    with pytest.raises((ConfigError, KeyError)):
        validate(_mutated(mutate))
