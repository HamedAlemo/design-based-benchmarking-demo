# M5 Monte Carlo

Goal: all replicates for all arms and budgets, with the summaries that the hypotheses are judged on.

## Before starting on full

1. Commit, then record the commit hash and the SHA-256 of docs/HYPOTHESES.md in reports/M5.md. From here on HYPOTHESES.md must not change.
2. Run the full pipeline on dev first with the dev profile (50 replicates). This is a smoke test, not evidence.

## Driver (`simulate/montecarlo.py`)

1. Loop over (arm, budget). Seeds: `SeedSequence(base_seed).spawn` gives one child per (arm, budget), in a fixed order listed in the config. Each child spawns one child per replicate. Log the integer seed of each replicate.
2. For each replicate, draw once and evaluate every arm that reuses the draw (A0 to A0w; A1 to B1 at all tau; D to E).
3. Estimates per model, as `Estimate` rows:
   - Design arms: every parameter. Linearized SE for ratio parameters; Rao-Wu bootstrap SE for F1_c, IoU_c, macroF1 and mIoU on the bootstrap subset (replicates 0 to S − 1).
   - Naive arms: every parameter; binomial SE for OA, UA_c and PA_c only.
   - A1 also reports chip-averaged mIoU, computed per chip from that chip's confusion, then averaged over chips.
4. Pairwise rows for each model pair:
   - OA difference in every replicate: design-based SE for design arms, McNemar z for naive arms.
   - macroF1 and F1_c differences on the bootstrap subset (design arms only). For naive arms, record the point difference only.
5. Secondary rows, arm D only: per-state domain estimates; model-assisted area_c for each model with its SE.
6. Parallelize over replicates with joblib processes. Each worker opens the memmaps read-only. Write one Parquet file per (arm, budget, tau) to `results/<extent>/mc/`. With `--resume`, skip files that are complete (row count check).
7. Evaluate the real CVPR test split once with the A0 and A0w estimators. Save it to `results/<extent>/mc/cvpr_actual.parquet`.

## Summaries (`simulate/metrics.py`, `simulate/ranking.py`)

Write to `results/<extent>/summary/` as Parquet and CSV:

1. `estimates_summary`, per (arm, budget, tau, model, parameter): R_def, undefined rate, mean, truth, bias, relative bias, MCSE(bias), RMSE, empirical SD, mean SE, SE ratio, coverage, MCSE(coverage), mean CI width. Truth scope: `all`; for B1 also the matching `restricted_tau` scope.
2. `ranking_summary`, per (arm, budget, tau, metric in OA / macroF1 / F1_c): probability of the true best model, mean Kendall tau-b against the true ranking, and the share of pairwise decisions that are correct-significant, not significant, Type S, and sign-flipped.
3. `efficiency_summary` (H5): CI width under D vs F per model, class and budget, with rho.
4. `domain_summary` and `area_summary` (secondary).

## Acceptance checks

| Check | Pass condition |
| --- | --- |
| Completeness | Expected row counts for every file |
| Reproducibility | Re-running two (arm, budget) combinations from scratch gives byte-identical Parquet content (compare a hash of the sorted rows) |
| No NaN leaks | NaN appears only where a ratio is undefined, and is counted in R_def |
| Runtime log | Wall time per arm and budget reported |
| Frozen hypotheses | HYPOTHESES.md hash unchanged since the start of M5 |

Do not interpret results against the hypotheses in M5. That happens in M6. Write reports/M5.md, update STATUS.md, commit (summaries and the report only; raw Monte Carlo files stay git-ignored).
