# M3 Estimators and validation

Goal: correct, tested estimators. No Monte Carlo runs until every check here passes. This is the milestone the skeptical audience will attack, so test it hard.

## Implementation (formulas in PROTOCOL.md section 6)

1. `params.py`: each ratio parameter as an indicator pair (y, x) on (map class m, ref class r):
   - OA: y = 1[m = r], x = 1
   - UA_c: y = 1[m = c and r = c], x = 1[m = c]
   - PA_c: y = 1[m = c and r = c], x = 1[r = c]
   - area_c: y = 1[r = c], x = 1
   - diff_OA(k, l): y = 1[m_k = r] − 1[m_l = r], x = 1
   - Plus `metrics_from_confusion(C)` for every parameter, including F1_c, IoU_c, macroF1 and mIoU, from a (weighted) 6 x 5 matrix. A zero denominator gives NaN, never 0.
2. `weighted.py`:
   - Element designs: weighted confusion via `np.add.at` or bincount with weights.
   - Cluster designs: sum of w_i x confusion_i over selected PSUs.
3. `variance.py`:
   - `var_ratio_element(y, x, w, stratum, N_h, n_h)`: z = (y − R x) / X_hat; V = sum_h N_h^2 (1 − n_h/N_h) s2_h / n_h, with s2_h the sample variance of z in stratum h (ddof = 1). Strata with n_h < 2 raise an error. Allocation guarantees n_h >= 2.
   - `var_ratio_cluster(Y_i, X_i, w_i, stratum_i, M_h, m_h)`: Y_i and X_i are PSU totals from the confusion arrays; t_i = (Y_i − R X_i) / X_hat; V = sum_h M_h^2 (1 − m_h/M_h) s2_t,h / m_h.
4. `naive.py`: pooled unweighted confusion; binomial SE for OA, UA_c and PA_c (n = the relevant pooled count); McNemar z = (b − c) / sqrt(b + c), with z = 0 when b + c = 0.
5. `bootstrap.py`: Rao-Wu rescaling bootstrap over units (cells or PSUs) within strata, B replicates, returning SE for any function of the weighted confusion. Seeded from the replicate's generator.
6. `paired.py`: design-based difference for OA (linearized) and for macroF1 and F1_c (bootstrap). Returns estimate, SE and CI.
7. `model_assisted.py`: post-stratified area estimator with known map proportions W_i^(k), and its linearized SE.

## Validation

1. Hand-worked unit tests: tiny populations with answers computed by hand in the test docstring:
   - one 2-stratum element sample with 8 cells
   - one 2-stratum cluster sample with 5 PSUs
   - UA, PA, OA, area and the variance formulas
2. Synthetic test populations (software tests only, not study results), generated inside the tests with a fixed seed:
   - Element case: N = 20,000 cells, 4 strata, 3 models with different class-specific error rates, including a rare class at about 2%.
   - Cluster case: 300 PSUs of unequal size in 2 strata, with intra-cluster correlation (cluster-level random effect on correctness).
   - Run 20,000 draws per design at two sample sizes.
   - Pass conditions: |mean estimate − truth| <= 3 MCSE for OA, UA_c, PA_c and area_c; mean(V_hat) / empirical variance in [0.9, 1.1] for OA at the larger sample size; OA coverage in [0.93, 0.97].
   - Also show the naive pooled SE under-covering in the cluster case. This is expected and documents that the test can detect it.
3. Real-data check on the dev cell table, 5,000 draws:
   - Stratified D design at n = 1000: OA bias within 3 MCSE of the dev truth for each model; coverage in [0.93, 0.97].
   - A0w on dev tiles: same check. If the dev extent has too few tiles per state for T = 5, use T = 3 and note it.
4. R survey cross-check (`tests/r_survey_check.R`):
   - Element: export one fixed stratified element sample (cells with y, x, w, stratum, N_h) to CSV. Run `svydesign(ids = ~1, strata = ~stratum, fpc = ~N_h, weights = ~w, data = d)` then `svyratio(~y, ~x, design)`.
   - Cluster: one fixed cluster sample at cell level, `ids = ~psu`, `fpc = ~M_h`.
   - Compare estimate and SE with ours for OA, one UA and one PA: relative difference below 1e-6.
   - Run R from Python via subprocess. Save the comparison table to reports/M3.md.
5. Bootstrap vs linearization: on 200 synthetic draws, the mean bootstrap SE for OA is within 10% of the linearized SE.
6. Truth isolation test still passes.

## Acceptance checks

| Check | Pass condition |
| --- | --- |
| Unit tests | All hand-worked tests pass |
| Synthetic unbiasedness | All bias checks within 3 MCSE |
| Variance ratio | OA in [0.9, 1.1], element and cluster |
| Coverage | OA in [0.93, 0.97], element and cluster |
| Real-data dev check | D and A0w pass |
| R survey | Relative difference < 1e-6 for estimate and SE |
| Bootstrap | Within 10% of linearization |
| Speed | One element estimate set (all models, all parameters, linearized SE) in under 20 ms at n = 2000; one cluster set in under 20 ms at 200 PSUs |

Write `reports/M3.md` with every number, update STATUS.md, commit.
