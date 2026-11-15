# CLAUDE.md: standing rules for this repository

You are building a methods experiment for a peer-reviewed paper. The audience is skeptical of design-based accuracy assessment, so correctness, traceability and honesty matter more than speed. Read `docs/PROTOCOL.md` and `docs/HYPOTHESES.md` before writing code in any session.

## What we are proving

Conventional GeoAI benchmark protocols (clustered tiles, class-balanced chips, purity filtering, unweighted pooled metrics) estimate the wrong population quantity and report overconfident uncertainty. A shared probability sample with known inclusion probabilities recovers true map accuracy and the true model ranking. The truth is known exactly because the reference map is wall-to-wall.

## Invariants (never violate)

1. Inclusion probabilities are first-class. Every sampler returns, for each sampled unit, `pi`, `stratum` and `psu` (see `src/bowpilot/contracts.py`). A unit the protocol excludes has `pi = 0` and is never silently dropped from the population definition.
2. Estimators never see the population truth. Only `truth.py` reads the full cell table for metrics. Add a test that fails if an estimator module imports truth.
3. No raster I/O inside the Monte Carlo loop. Monte Carlo reads the cell table memmaps and the precomputed per-unit arrays only.
4. Determinism. All randomness comes from `numpy.random.Generator(PCG64)` seeded through `SeedSequence(config.montecarlo.base_seed).spawn(...)`. Seeds are logged with every result row. Re-running with the same seed must give identical output.
5. The population is fixed in M2 and never redefined later. If a later milestone suggests changing it, stop, record the issue in `docs/DECISIONS.md`, and ask.
6. `docs/HYPOTHESES.md` is frozen once M5 starts. Never tune criteria after seeing results.
7. Configuration over code. Class codes, crosswalks, budgets, thresholds and seeds live in `config/`. No magic numbers in modules.
8. Report what you see, including results that weaken our argument. H0 exists for this.

## Working method

- Work milestone by milestone, in order. Each milestone spec in `docs/milestones/` lists deliverables and acceptance checks.
- Run every milestone first on `extent: dev`, then on `extent: full`. Dev runs use the smaller Monte Carlo settings in `config/montecarlo.yaml`.
- After each milestone:
  1. Run `pytest -q` and `ruff check .`. Both must pass.
  2. Write `reports/Mx.md`: what was built, every acceptance check with its number and pass/fail, deviations, runtime, disk used.
  3. Update the milestone's line in `reports/STATUS.md`.
  4. `git add -A && git commit -m "Mx: <summary>"`.
- Any deviation from the protocol, however small, gets an entry in `docs/DECISIONS.md`: date, what, why, and expected effect on results.
- If an acceptance check fails, diagnose and fix. After two documented failed attempts, stop and write the problem at the top of the milestone report.

## Stop and wait for a human only when

1. Earth Engine authentication is missing or fails.
2. The reference product's class names do not match `config/classes.yaml` expectations.
3. An acceptance check fails after two documented fix attempts.
4. Free disk drops below 20 GB.
5. A step would redefine the population or change a pre-registered criterion.

Otherwise keep going. When blocked on one step, finish any independent work first (for example, download other products while waiting on Earth Engine).

## Engineering standards

- Python 3.11, environment from `environment.yml`. Install the package with `pip install -e .`.
- Type hints on public functions. Docstrings state units and array shapes.
- Vectorize with numpy. Use windowed raster reads (rasterio) with joblib or dask for parallelism. Never load the full 1 m reference into memory.
- Large per-cell arrays are `.npy` memmaps in `data/interim/cells/`, one file per column. Tables of results are Parquet.
- Tests in `tests/`. Estimator and sampler tests are mandatory (see M3 and M4).
- Log with the standard `logging` module to `logs/<milestone>_<timestamp>.log`.
- Data folders `data/` and `results/` are git-ignored. Reports and figures are committed.

## Writing style for reports

Plain, specific, numbers with units. No em dashes. Do not use bold text. Short sentences. Tables for numbers. State failures plainly.
