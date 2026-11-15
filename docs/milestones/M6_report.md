# M6 Figures, tables and results

Goal: the six figures, two tables, and `reports/RESULTS.md`, which applies the frozen criteria in HYPOTHESES.md to the full-extent summaries.

## Figures (`report/figures.py`)

Save PNG at 300 dpi and PDF to `results/figures/`, and copy the PNGs to `reports/figures/`.

Shared style:
- Matplotlib, white background, readable at single-column width.
- Arm colors by group, consistent across figures: conventional in reds (A0, A1), repair in ambers (A0w, B1, B2), design in blues (C, D, D2), the mistake in grey (E), per-model reference in purple (F).
- Colorblind-safe palette; markers differ by arm as well as color.
- The real CVPR test split is marked with a distinct star wherever it applies.

Figures:

1. Estimates vs truth. Rows: OA, macroF1, UA of barren. For each model, show one typical replicate per arm (the replicate whose OA estimate is closest to that arm's mean): point and 95% CI, with a vertical line at the truth. Fixed budget: n = 1000, T = 10, 100 chips, tau = 0.9.
2. Ranking fidelity vs budget. Left panel: probability of the true best model on OA by arm across budgets. Right panel: Type S rate for OA pairs, with a dashed line at 0.025. Conventional budgets are on their own axis (labeled cells per draw, log scale) so labeling cost is visible.
3. Coverage. OA coverage by arm and budget, with a band at 0.93 to 0.97, and the SE ratio as a second panel.
4. Decomposition bridge (waterfall). OA bias for one model, chosen as the one with the largest A1 bias: A1(0.9) to B1(0.9) to B1(0) to B2, and separately A0 to A0w. Error bars show 2 MCSE.
5. Study area. Panels: reference class map, D strata, and one draw of sample locations for C, D, A0 (tiles), A1 (chips). Use the full extent, with a dev inset if helpful.
6. Efficiency (H5). For each model, mean CI width of UA_c and PA_c under D vs F at each budget. Secondary axis: total labels (D: n; F: 3n).

After saving, open every PNG and check it: labels readable, no overlap, legend complete, truth lines visible. Fix and re-render as needed.

## Tables (`report/tables.py`)

- Table 1: true population metrics per model (OA, macroF1, UA_c, PA_c, area_c), with state columns in the supplement.
- Table 2: OA and macroF1 bias, RMSE and coverage by arm and budget.
- Supplementary tables: the full estimates and ranking summaries, as CSV.

## RESULTS.md (`report/results_md.py`, then edited by you)

Structure:
1. Summary for the PI. Five to eight sentences with the headline numbers.
2. One section per hypothesis H1 to H5, then H0. Each section has:
   - the criterion, quoted from HYPOTHESES.md
   - the numbers that decide it, in a table
   - the verdict: Supported, Not supported, or Partially supported. Use Partially only if the criterion has parts and some fail; say which.
   - one or two sentences of interpretation, with no overclaiming
3. Surprises and limitations, including anything that weakens the argument.
4. Reproducibility: commit hash, seeds, runtime, data versions.

## Adversarial review (required)

Spawn a fresh subagent that has not seen your reasoning. Give it RESULTS.md, HYPOTHESES.md and the summary CSVs. Ask it to check that every verdict follows mechanically from the criterion and the numbers, that every number matches the CSVs, and that no sentence overclaims. Fix what it finds and append its findings and your fixes to the end of RESULTS.md.

## Acceptance checks

| Check | Pass condition |
| --- | --- |
| Figures | Six figures exist in both formats and have been visually checked |
| Tables | Generated from results/ alone (rerun `bowpilot report` from a clean results/figures/) |
| Verdicts | Each hypothesis has a verdict traceable to numbers in the summaries |
| Review | Adversarial review done and logged |

Update STATUS.md and commit.
