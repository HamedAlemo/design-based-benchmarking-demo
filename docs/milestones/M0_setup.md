# M0 Setup

Goal: a working environment, the package skeleton below, a config loader and a CLI, so later milestones only add logic.

## Steps

1. Create the conda environment: `conda env create -f environment.yml && conda activate bowpilot && pip install -e .`. If an environment named `bowpilot` exists, update it instead.
2. Create the package layout exactly as below. Each module starts with a docstring stating its responsibility; functions are added in later milestones.

```text
src/bowpilot/
  __init__.py
  contracts.py            # given; do not change without a DECISIONS.md entry
  config.py               # load + validate all YAML in config/, resolve active extent, expose a typed Config
  cli.py                  # typer app: one command per milestone step (below)
  grid.py                 # analysis grid: CRS, transform, shape, bbox -> window, cell index <-> row/col
  logging_utils.py        # logs/<step>_<timestamp>.log + console
  data/
    boundaries.py         # Census cartographic boundaries -> MD/DE polygons in grid CRS
    reference.py          # ScienceBase discovery + download, class inspection, 1 m -> 10 m aggregation
    products.py           # WorldCover + Esri/IO (Planetary Computer), Dynamic World (Earth Engine)
    ecoregions.py         # EPA Level III download + rasterize
    cvpr.py               # CVPR spatial index download + filter
    qa.py                 # quicklooks, alignment shift test, class distribution tables
  population/
    cell_table.py         # population mask + per-column memmaps
    frames.py             # tile frame, chip frame, rare-class tags, strata for D, D2, F
    units.py              # per-PSU confusion and discordant arrays (tiles; chips x purity thresholds)
    truth.py              # population truth (the ONLY module that computes metrics on the full table)
  estimation/
    params.py             # parameter definitions as (y, x) indicator pairs; metrics from a confusion matrix
    weighted.py           # weighted error matrix + ratio estimates (element and cluster)
    variance.py           # linearization variance: stratified element, stratified one-stage cluster
    naive.py              # pooled unweighted estimates, binomial SE, McNemar
    bootstrap.py          # Rao-Wu rescaling bootstrap
    paired.py             # paired differences between models
    model_assisted.py     # post-stratified area estimator using a model map
  sampling/
    allocation.py         # minimum + Neyman / proportional allocation with caps
    element.py            # SRS and stratified SRS of cells
    cluster.py            # SRS of tiles per state; equal-per-tag chip selection with redistribution
    arms.py               # registry: arm name -> sampler, estimator, draws_from
  simulate/
    montecarlo.py         # driver with checkpoint / resume
    metrics.py            # bias, MCSE, RMSE, SE ratio, coverage, CI width
    ranking.py            # best-model, Kendall tau, pairwise decision classes, Type S
  report/
    figures.py
    tables.py
    results_md.py
tests/
  test_config.py
  test_truth_isolation.py
  (later) test_estimators_*.py, test_sampling_*.py, test_montecarlo_*.py
  r_survey_check.R
```

3. CLI commands (typer), each accepting `--extent dev|full` (default from `config/extent.yaml`):
   - `bowpilot data` (M1), `bowpilot population` (M2), `bowpilot validate-estimators` (M3), `bowpilot validate-sampling` (M4), `bowpilot montecarlo` (M5, with `--resume`), `bowpilot report` (M6), `bowpilot status`.
   - Data paths are namespaced by extent: `data/<extent>/raw`, `data/<extent>/interim`, `results/<extent>/...`.
4. `config.py` validates: budgets are positive integers; purity thresholds sorted in [0, 1]; every product crosswalk maps into 0..5; arms with `draws_from` point to an existing arm; the montecarlo profile exists.
5. `tests/test_truth_isolation.py`: fails if any module under `estimation/`, `sampling/` or `simulate/` imports `bowpilot.population.truth`.

## Acceptance checks

| Check | Pass condition |
| --- | --- |
| Environment | `python -c "import rasterio, geopandas, ee, pystac_client, planetary_computer, sciencebasepy"` succeeds; `Rscript -e "library(survey)"` succeeds |
| Package | `pip install -e .` works; `bowpilot --help` lists all commands |
| Config | `pytest tests/test_config.py` passes |
| Isolation test | present and passing |
| Lint | `ruff check .` clean |
| Earth Engine | `python -c "import ee; ee.Initialize(project=...)"` succeeds. If not: record in reports/M0.md as a pending human gate and continue (it blocks only the Dynamic World step in M1) |

Write `reports/M0.md`, update `reports/STATUS.md`, commit.
