# Pre-registered hypotheses and decision criteria

Frozen when M5 starts on the full extent (record the commit hash in `reports/M5.md`). Dev-extent results are never used to tune these criteria. Verdicts come only from the full-extent Monte Carlo.

## Definitions

- Design set: arms whose estimator is design-consistent for the full population: C, D, D2, F, A0w, B2.
- Conventional set: A0, A1 (each tau), E.
- Restricted arms: B1(tau). They target a restricted population (complete chips, purity at least tau) and are judged under H4.
- R_def: replicates in which an estimate is defined (a ratio with a zero denominator, such as UA of a class absent from the sample, is undefined). Undefined rates are always reported.
- Bias = mean(estimate) − truth over R_def. MCSE(bias) = SD(estimate) / sqrt(R_def).
- Coverage = share of R_def replicates whose 95% CI contains the truth. MCSE(coverage) = sqrt(c (1 − c) / R_def).
- Type S: a pairwise decision that is statistically significant with the wrong sign.
- All accuracy quantities are proportions in [0, 1]; "1 point" = 0.01.

## H1 Bias

Claim: conventional arms are biased for population accuracy; design arms are not.

Supported if both hold:
1. Design set, at every budget: for OA and macroF1 of every model, |bias| <= max(2 MCSE, 0.002). For UA_c, PA_c and area_c, at least 95% of (model, class, budget) combinations with R_def >= 0.95 R satisfy |bias| <= max(2 MCSE, 0.005).
2. Conventional set: at least one arm has |bias| > max(2 MCSE, 0.01) for OA or macroF1 of at least one model.

Always report the full bias table for every arm.

## H2 Uncertainty

Claim: naive SEs from clustered or unweighted samples under-cover; design SEs reach nominal coverage.

Supported if both hold:
1. Design set: OA coverage within [0.93, 0.97] at every budget for every model; UA_c and PA_c coverage >= 0.90 for at least 90% of combinations with R_def >= 0.95 R.
2. A0 OA coverage < 0.90 at every T for at least two of three models.

Report the SE ratio (mean estimated SE / empirical SD) for every arm.

## H3 Ranking

Claim: design arms rarely produce confidently wrong comparisons; conventional arms can, or pick the wrong best model more often.

Supported if both hold:
1. Design set: Type S rate for OA pairs <= 0.025 + 2 MCSE at every budget.
2. At least one conventional arm meets one of: Type S rate for OA pairs > 0.05 (McNemar on pooled pixels), or probability of selecting the true best model on OA or macroF1 at least 0.10 lower than arm C at n = 500.

If neither part of condition 2 occurs and the true OA gaps between models exceed 0.02, report this as an H0 outcome, not a failure.

## H4 Purity filtering

Claim: purity filtering inflates accuracy, and weighting cannot repair it because excluded cells have zero inclusion probability.

Supported if all hold:
1. B1(tau) OA bias against the full-population truth increases with tau (0.75 < 0.9 < 1.0) for every model, and B1(1.0) OA bias > max(2 MCSE, 0.01) for every model.
2. B1(tau) is consistent for its restricted truth: |mean B1(tau) − restricted truth(tau)| <= max(2 MCSE, 0.002) for OA.
3. B2 meets the H1 design-set criterion.

## H5 Efficiency of a shared sample

Claim: one model-agnostic stratified sample (D) gives per-model UA and PA precision close to per-model stratified samples (F) at one-Kth of the labeling cost.

Measure: rho = mean CI width under D / mean CI width under F, for each model, class and budget, for UA_c and PA_c.

Supported if the median rho over (model, class) is <= 1.25 at n = 1000 and at n = 2000. Also report the maximum rho and the classes where D is weakest, and the cost ratio (F labels = 3 x D labels).

## H0 Honest null (reported, no pass or fail)

For each conventional arm and budget: share of replicates whose OA and macroF1 rankings equal the true rankings. Where this share is >= 0.95 while H1 shows bias, label the case "ranking robust, absolute values biased". Report true OA and macroF1 gaps between models, since small gaps make ranking hard for every design.
