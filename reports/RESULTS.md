# Results: design-based vs conventional benchmarking, Chesapeake pilot (full extent)

Generated from `results/full/summary/` (1,000 Monte Carlo replicates per arm and budget), then edited by hand. Criteria are quoted from `docs/HYPOTHESES.md`, frozen at commit 9eaa7dbfc43ee5aaf3e38406fa0250a412f2076a (SHA-256 7cba572b17ce2618110cec61be3c81b03fff97edaf553b500d079c0d7de12e75) before any full-extent replicate was run.

## 1. Summary for the PI

The population is 318,425,338 cells of 10 m in Maryland and Delaware with a wall-to-wall 1 m reference. True OA: WorldCover 0.853, Dynamic World 0.772, Esri/IO 0.766. The DW vs IO gap is only 0.006, and its sign flips by state.

The conventional tile benchmark (A0, equal tiles per state, pooled and unweighted) made a significant wrong-sign call (Type S) on the DW vs IO pair in 51% to 59% of draws. Type S rate over all OA pairs: 0.17 to 0.20, rising with the number of tiles. On the real CVPR test split it ranks IO above DW with McNemar z = -11.5. Its OA confidence intervals covered the truth in 0.5% to 1.6% of draws.

Purity filtering raised OA above the true population value for every model: A1 by +0.036 (tau 0.75) to +0.094 (tau 1.0), B1 by +0.048 to +0.108. Correct weighting cannot remove this: B1 estimates its restricted population to within 0.0015 but stays 0.05 to 0.11 above the full-population truth.

The design-based arms estimated OA with |bias| at most 0.0023. OA coverage was 0.933 to 0.960 for C, D, D2 and F, and 0.921 to 0.970 for B2. The weighted tile arm A0w under-covered OA (0.83 to 0.93) at every number of tiles. Their Type S rate was at most 0.010.

The pre-registered design-arm criteria cover more than OA, and they fail. Small-sample bias in macroF1 (up to 0.034 for A0w, 0.020 for D2, 0.021 for F) and in rare-class UA/PA fails H1 condition 1. OA under-coverage in A0w (and B2 at one budget) and under-coverage of rare-class UA/PA intervals fail H2 condition 1. Bootstrap intervals for macroF1 also under-cover badly in C and D2 at small n (0.40 to 0.53 at n = 500). H3 and H5 are supported. A shared stratified sample (D) gave median UA/PA precision similar to per-model samples (F) at one third of the labelling cost (median rho 0.90 to 0.93). For barren UA, though, D is 2 to 3.8 times less precise than F and its intervals under-cover.

Verdicts: H1, H2 and H4: criterion not met (HYPOTHESES.md requires all conditions; at least one fails). Under the M6 reporting convention these are labelled "Partially supported", because their other conditions hold. H3 and H5: Supported.

## 2. Setup in brief

| Item | Value |
| --- | --- |
| Population N | 318,425,338 cells (MD 266,353,825; DE 52,071,513) |
| Models | WC = ESA WorldCover 2021 v200; DW = Dynamic World 2021 (annual mode); IO = Esri/IO 2021 v02 |
| Tile frame | 1,045 quarter quadrangles: 881 MD, 164 DE |
| Chip frame | 80,397 chips of 640 m; 75,191 complete |
| Replicates | 1,000 per arm and budget; bootstrap SE (Rao-Wu, B = 200) on replicates 0 to 199 |
| Interpretation | Design-set conditions are applied to each design arm separately. "Every budget" means every configured budget. |

True metrics (Table 1, `results/full/tables/table1_truth.csv`):

| Model | OA | macroF1 | OA MD | OA DE |
| --- | --- | --- | --- | --- |
| WC | 0.8528 | 0.7279 | 0.8531 | 0.8508 |
| DW | 0.7720 | 0.6731 | 0.7772 | 0.7455 |
| IO | 0.7662 | 0.6326 | 0.7665 | 0.7647 |

True gaps: WC - DW OA 0.0808, WC - IO 0.0865, DW - IO 0.0058; macroF1 0.0548, 0.0952, 0.0405.

## 3. Hypotheses

Notation: bias = mean(estimate) - truth over R_def; MCSE = SD / sqrt(R_def); "tol" is the criterion's tolerance.

### H1 Bias

Criterion (HYPOTHESES.md): "Supported if both hold: 1. Design set, at every budget: for OA and macroF1 of every model, |bias| <= max(2 MCSE, 0.002). For UA_c, PA_c and area_c, at least 95% of (model, class, budget) combinations with R_def >= 0.95 R satisfy |bias| <= max(2 MCSE, 0.005). 2. Conventional set: at least one arm has |bias| > max(2 MCSE, 0.01) for OA or macroF1 of at least one model."

OA bias by arm and budget:

| key | WC | DW | IO |
| --- | --- | --- | --- |
| A0 5 | -0.0020 | -0.0123 | -0.0026 |
| A0 10 | -0.0009 | -0.0101 | -0.0001 |
| A0 20 | -0.0008 | -0.0100 | -0.0004 |
| A0w 5 | -0.0009 | -0.0016 | -0.0023 |
| A0w 10 | 0.0002 | 0.0006 | 0.0013 |
| A0w 20 | -0.0003 | -0.0000 | -0.0006 |
| A1 50 t0.75 | 0.0393 | 0.0414 | 0.0358 |
| A1 100 t0.75 | 0.0395 | 0.0412 | 0.0358 |
| A1 200 t0.75 | 0.0394 | 0.0418 | 0.0360 |
| A1 50 t0.9 | 0.0644 | 0.0676 | 0.0631 |
| A1 100 t0.9 | 0.0647 | 0.0675 | 0.0633 |
| A1 200 t0.9 | 0.0647 | 0.0682 | 0.0634 |
| A1 50 t1.0 | 0.0858 | 0.0935 | 0.0911 |
| A1 100 t1.0 | 0.0862 | 0.0935 | 0.0915 |
| A1 200 t1.0 | 0.0861 | 0.0942 | 0.0916 |
| B1 50 t0.0 | -0.0001 | 0.0014 | -0.0009 |
| B1 100 t0.0 | 0.0006 | 0.0022 | 0.0005 |
| B1 200 t0.0 | 0.0001 | 0.0024 | -0.0001 |
| B1 50 t0.75 | 0.0501 | 0.0482 | 0.0475 |
| B1 100 t0.75 | 0.0508 | 0.0491 | 0.0491 |
| B1 200 t0.75 | 0.0506 | 0.0496 | 0.0487 |
| B1 50 t0.9 | 0.0765 | 0.0757 | 0.0765 |
| B1 100 t0.9 | 0.0772 | 0.0765 | 0.0781 |
| B1 200 t0.9 | 0.0771 | 0.0772 | 0.0779 |
| B1 50 t1.0 | 0.0986 | 0.1027 | 0.1062 |
| B1 100 t1.0 | 0.0992 | 0.1035 | 0.1079 |
| B1 200 t1.0 | 0.0993 | 0.1043 | 0.1076 |
| B2 50 | 0.0001 | -0.0003 | -0.0000 |
| B2 100 | 0.0005 | 0.0012 | 0.0014 |
| B2 200 | -0.0002 | -0.0007 | -0.0006 |
| C 500 | -0.0001 | -0.0003 | -0.0000 |
| C 1000 | -0.0005 | 0.0001 | -0.0005 |
| C 2000 | 0.0002 | 0.0003 | 0.0002 |
| D 500 | -0.0005 | -0.0003 | -0.0006 |
| D 1000 | -0.0002 | -0.0004 | -0.0002 |
| D 2000 | -0.0003 | -0.0002 | -0.0000 |
| D2 500 | -0.0001 | -0.0004 | 0.0001 |
| D2 1000 | 0.0001 | -0.0001 | 0.0004 |
| D2 2000 | 0.0002 | 0.0001 | 0.0004 |
| E 500 | -0.0556 | -0.1182 | -0.1488 |
| E 1000 | -0.0553 | -0.1194 | -0.1488 |
| E 2000 | -0.0529 | -0.1125 | -0.1306 |
| F 500 | 0.0016 | -0.0001 | -0.0005 |
| F 1000 | -0.0001 | -0.0001 | -0.0004 |
| F 2000 | 0.0005 | -0.0001 | -0.0001 |

Largest |OA bias| in the design set: 0.0023 (B1 is not in the design set). Every design-arm OA bias satisfies the tolerance. macroF1 bias:

| key | WC | DW | IO |
| --- | --- | --- | --- |
| A0 5 | -0.0266 | -0.0294 | -0.0267 |
| A0 10 | -0.0155 | -0.0181 | -0.0162 |
| A0 20 | -0.0104 | -0.0128 | -0.0105 |
| A0w 5 | -0.0335 | -0.0345 | -0.0319 |
| A0w 10 | -0.0180 | -0.0189 | -0.0174 |
| A0w 20 | -0.0096 | -0.0103 | -0.0093 |
| A1 50 t0.75 | 0.0562 | 0.0356 | 0.0113 |
| A1 100 t0.75 | 0.0594 | 0.0391 | 0.0139 |
| A1 200 t0.75 | 0.0614 | 0.0426 | 0.0177 |
| A1 50 t0.9 | 0.0844 | 0.0542 | 0.0238 |
| A1 100 t0.9 | 0.0878 | 0.0580 | 0.0265 |
| A1 200 t0.9 | 0.0897 | 0.0616 | 0.0305 |
| A1 50 t1.0 | 0.1096 | 0.0723 | 0.0355 |
| A1 100 t1.0 | 0.1131 | 0.0765 | 0.0385 |
| A1 200 t1.0 | 0.1149 | 0.0802 | 0.0427 |
| B2 50 | -0.0070 | -0.0061 | -0.0072 |
| B2 100 | -0.0031 | -0.0010 | -0.0021 |
| B2 200 | -0.0022 | -0.0016 | -0.0019 |
| C 500 | -0.0120 | -0.0135 | -0.0094 |
| C 1000 | -0.0074 | -0.0073 | -0.0060 |
| C 2000 | -0.0043 | -0.0046 | -0.0046 |
| D 500 | 0.0070 | 0.0083 | 0.0097 |
| D 1000 | 0.0030 | 0.0037 | 0.0038 |
| D 2000 | 0.0007 | 0.0023 | 0.0026 |
| D2 500 | -0.0197 | -0.0171 | -0.0115 |
| D2 1000 | -0.0093 | -0.0121 | -0.0087 |
| D2 2000 | -0.0031 | -0.0033 | -0.0016 |
| E 500 | 0.0646 | 0.0173 | 0.0035 |
| E 1000 | 0.0655 | 0.0160 | 0.0035 |
| E 2000 | 0.0560 | 0.0204 | 0.0121 |
| F 500 | 0.0123 | 0.0100 | 0.0206 |
| F 1000 | 0.0047 | 0.0058 | 0.0076 |
| F 2000 | 0.0030 | 0.0017 | 0.0026 |

Condition 1, macroF1 part: 48 of 54 design (arm, budget, model) cells fail, in every design arm at its smallest budget. Signs differ by design: negative for A0w, B2, C and D2, positive for D and F. The bias shrinks as the budget grows, for example C -0.012 / -0.007 / -0.004 for WC at n = 500 / 1000 / 2000.

Condition 1, class part (share of (model, class, budget) cells within tolerance, R_def >= 0.95 R):

| Arm | Share within tolerance | Cells | Meets 95% |
| --- | --- | --- | --- |
| A0w | 0.585 | 135 | no |
| B2 | 0.822 | 135 | no |
| C | 1.000 | 125 | yes |
| D | 0.867 | 135 | no |
| D2 | 0.984 | 125 | yes |
| F | 0.911 | 135 | no |

All 18 of D's failing cells are barren (class 4) UA or PA. A0w fails in every class (water 17, barren 16, impervious 16, low vegetation 5, tree 2 cells). F's barren PA bias is +0.117 to +0.138 at n = 500.

C and D2 have 125 eligible cells, not 135. The R_def >= 0.95 R rule drops 10 barren cells each, the hardest ones; some would fail (for example C n = 500 DW UA_4: bias 0.043, tolerance 0.033). C's share of 1.000 is therefore partly a consequence of the eligibility rule. Undefined rates are reported in section 3.7.

Condition 2: met, unambiguously through A1 and E. Every A1 setting is biased upward for OA (+0.036 to +0.094), and E downward (-0.053 to -0.149). A0's OA bias exceeds the tolerance only for DW at T = 5 and 10 (-0.012, -0.010; at T = 20 it is -0.00999, just inside). It is at most 0.0026 for WC and IO. A0's macroF1 bias (-0.010 to -0.029) is no larger than that of the correctly weighted A0w on the same tiles (-0.009 to -0.035), so it is finite-sample macroF1 bias, not an effect of ignoring the weights.

- Condition 1: not met (macroF1 in all design arms; class-level share in A0w, B2, D and F).
- Condition 2: met.

Verdict: Criterion not met; labelled Partially supported (M6 convention). Condition 1 fails in every design arm; condition 2 holds.

Interpretation: For OA, a ratio of totals, every design arm is unbiased within 0.0023 at every budget, while the conventional arms are biased by up to 0.15. The criterion also covers macroF1 and rare-class UA/PA. These are nonlinear or small-denominator statistics, and at 500 to 2,000 labelled cells or 5 to 20 tiles per state their design-based estimates carry finite-sample bias that the criterion does not tolerate. This is a real limitation of design-based estimation at these budgets for classes covering 0.5% (barren) to 6% (water) of the area.

### H2 Uncertainty

Criterion: "Supported if both hold: 1. Design set: OA coverage within [0.93, 0.97] at every budget for every model; UA_c and PA_c coverage >= 0.90 for at least 90% of combinations with R_def >= 0.95 R. 2. A0 OA coverage < 0.90 at every T for at least two of three models."

OA coverage (MCSE about 0.007 near 0.95):

| key | WC | DW | IO |
| --- | --- | --- | --- |
| A0 5 | 0.012 | 0.005 | 0.010 |
| A0 10 | 0.010 | 0.006 | 0.011 |
| A0 20 | 0.016 | 0.010 | 0.008 |
| A0w 5 | 0.829 | 0.836 | 0.832 |
| A0w 10 | 0.881 | 0.890 | 0.871 |
| A0w 20 | 0.915 | 0.924 | 0.926 |
| A1 50 t0.75 | 0.000 | 0.006 | 0.018 |
| A1 100 t0.75 | 0.000 | 0.000 | 0.004 |
| A1 200 t0.75 | 0.000 | 0.000 | 0.000 |
| A1 50 t0.9 | 0.000 | 0.001 | 0.000 |
| A1 100 t0.9 | 0.000 | 0.000 | 0.000 |
| A1 200 t0.9 | 0.000 | 0.000 | 0.000 |
| A1 50 t1.0 | 0.000 | 0.000 | 0.000 |
| A1 100 t1.0 | 0.000 | 0.000 | 0.000 |
| A1 200 t1.0 | 0.000 | 0.000 | 0.000 |
| B1 50 t0.0 | 0.916 | 0.929 | 0.935 |
| B1 100 t0.0 | 0.937 | 0.939 | 0.946 |
| B1 200 t0.0 | 0.942 | 0.940 | 0.944 |
| B1 50 t0.75 | 0.074 | 0.357 | 0.456 |
| B1 100 t0.75 | 0.011 | 0.196 | 0.173 |
| B1 200 t0.75 | 0.000 | 0.033 | 0.025 |
| B1 50 t0.9 | 0.016 | 0.141 | 0.104 |
| B1 100 t0.9 | 0.000 | 0.045 | 0.004 |
| B1 200 t0.9 | 0.000 | 0.001 | 0.000 |
| B1 50 t1.0 | 0.005 | 0.089 | 0.013 |
| B1 100 t1.0 | 0.000 | 0.006 | 0.000 |
| B1 200 t1.0 | 0.000 | 0.001 | 0.000 |
| B2 50 | 0.942 | 0.945 | 0.933 |
| B2 100 | 0.921 | 0.923 | 0.931 |
| B2 200 | 0.970 | 0.949 | 0.954 |
| C 500 | 0.952 | 0.933 | 0.952 |
| C 1000 | 0.955 | 0.954 | 0.949 |
| C 2000 | 0.934 | 0.956 | 0.954 |
| D 500 | 0.945 | 0.947 | 0.944 |
| D 1000 | 0.940 | 0.942 | 0.957 |
| D 2000 | 0.957 | 0.960 | 0.953 |
| D2 500 | 0.955 | 0.952 | 0.956 |
| D2 1000 | 0.938 | 0.943 | 0.948 |
| D2 2000 | 0.957 | 0.945 | 0.951 |
| E 500 | 0.092 | 0.000 | 0.000 |
| E 1000 | 0.004 | 0.000 | 0.000 |
| E 2000 | 0.000 | 0.000 | 0.000 |
| F 500 | 0.950 | 0.941 | 0.949 |
| F 1000 | 0.949 | 0.948 | 0.955 |
| F 2000 | 0.960 | 0.952 | 0.955 |

Condition 1a fails for A0w at every T (0.829 to 0.926) and for B2 at 100 chips (WC 0.921, DW 0.923; IO 0.931). C, D, D2 and F are inside [0.93, 0.97] everywhere (0.933 to 0.960).

Condition 1b (share of UA/PA cells with coverage >= 0.90): A0w 0.122, B2 0.589, C 0.850, D 0.711, D2 0.775, F 0.900. Only F meets 90%, exactly on the boundary (81 of 90 cells). Failures concentrate in water and barren; B2 also fails impervious in 8 cells. B2 at 200 chips has WC OA coverage 0.970, also on the boundary of condition 1a.

OA SE ratio (mean SE / empirical SD) for every arm, all budgets and models:

| Arm | SE ratio range | Arm | SE ratio range |
| --- | --- | --- | --- |
| A0 | 0.006 to 0.009 | C | 0.961 to 1.032 |
| A0w | 0.905 to 0.979 | D | 0.983 to 1.041 |
| A1 | 0.045 to 0.077 | D2 | 0.943 to 1.033 |
| B1 | 0.866 to 1.033 | E | 1.061 to 1.424 |
| B2 | 0.932 to 1.017 | F | 0.973 to 1.029 |

Condition 2: A0 OA coverage is 0.005 to 0.016 at every T for all three models.

- Condition 1a: not met (A0w; B2 at 100 chips).
- Condition 1b: not met (all design arms except F).
- Condition 2: met.

Verdict: Criterion not met; labelled Partially supported (M6 convention). Condition 1 fails; condition 2 holds.

Interpretation: The naive pooled SE for A0 is wrong by two orders of magnitude (SE ratio 0.006 to 0.009): it treats millions of clustered pixels as independent. Design SEs are close for OA in element designs (SE ratios 0.94 to 1.04). They fall short for cluster designs with few PSUs (A0w SE ratio 0.90 to 0.98, the small-sample Wald behaviour already seen in M3, DECISIONS.md entry 25) and for rare-class UA/PA, where Wald intervals around skewed ratios under-cover.

### H3 Ranking

Criterion: "Supported if both hold: 1. Design set: Type S rate for OA pairs <= 0.025 + 2 MCSE at every budget. 2. At least one conventional arm meets one of: Type S rate for OA pairs > 0.05 (McNemar on pooled pixels), or probability of selecting the true best model on OA or macroF1 at least 0.10 lower than arm C at n = 500."

OA pairwise decisions (3 pairs x 1,000 replicates per row):

| arm | budget | tau | type_s | mcse_type_s | sign_flip | p_ranking_exact |
| --- | --- | --- | --- | --- | --- | --- |
| A0 | 5 | 0.0000 | 0.1693 | 0.0068 | 0.1723 | 0.4830 |
| A0 | 10 | 0.0000 | 0.1837 | 0.0071 | 0.1850 | 0.4450 |
| A0 | 20 | 0.0000 | 0.1977 | 0.0073 | 0.1993 | 0.4020 |
| A0w | 5 | 0.0000 | 0.0097 | 0.0018 | 0.1260 | 0.6220 |
| A0w | 10 | 0.0000 | 0.0050 | 0.0013 | 0.1240 | 0.6280 |
| A0w | 20 | 0.0000 | 0.0010 | 0.0006 | 0.0973 | 0.7080 |
| A1 | 50 | 0.7500 | 0.0747 | 0.0048 | 0.0840 | 0.7480 |
| A1 | 50 | 0.9000 | 0.0827 | 0.0050 | 0.0913 | 0.7260 |
| A1 | 50 | 1.0000 | 0.0947 | 0.0053 | 0.1070 | 0.6790 |
| A1 | 100 | 0.7500 | 0.0563 | 0.0042 | 0.0663 | 0.8010 |
| A1 | 100 | 0.9000 | 0.0687 | 0.0046 | 0.0750 | 0.7750 |
| A1 | 100 | 1.0000 | 0.0840 | 0.0051 | 0.0907 | 0.7280 |
| A1 | 200 | 0.7500 | 0.0313 | 0.0032 | 0.0380 | 0.8860 |
| A1 | 200 | 0.9000 | 0.0420 | 0.0037 | 0.0473 | 0.8580 |
| A1 | 200 | 1.0000 | 0.0610 | 0.0044 | 0.0687 | 0.7940 |
| B1 | 50 | 0.0000 | 0.0003 | 0.0003 | 0.0943 | 0.7170 |
| B1 | 50 | 0.7500 | 0.0003 | 0.0003 | 0.1083 | 0.6750 |
| B1 | 50 | 0.9000 | 0.0003 | 0.0003 | 0.1190 | 0.6430 |
| B1 | 50 | 1.0000 | 0.0007 | 0.0005 | 0.1330 | 0.6010 |
| B1 | 100 | 0.0000 | 0.0000 | 0.0000 | 0.0850 | 0.7450 |
| B1 | 100 | 0.7500 | 0.0003 | 0.0003 | 0.1033 | 0.6900 |
| B1 | 100 | 0.9000 | 0.0010 | 0.0006 | 0.1140 | 0.6580 |
| B1 | 100 | 1.0000 | 0.0020 | 0.0008 | 0.1393 | 0.5820 |
| B1 | 200 | 0.0000 | 0.0000 | 0.0000 | 0.0610 | 0.8170 |
| B1 | 200 | 0.7500 | 0.0007 | 0.0005 | 0.0847 | 0.7460 |
| B1 | 200 | 0.9000 | 0.0010 | 0.0006 | 0.1020 | 0.6940 |
| B1 | 200 | 1.0000 | 0.0020 | 0.0008 | 0.1343 | 0.5970 |
| B2 | 50 | 0.0000 | 0.0023 | 0.0009 | 0.1167 | 0.6500 |
| B2 | 100 | 0.0000 | 0.0000 | 0.0000 | 0.1033 | 0.6900 |
| B2 | 200 | 0.0000 | 0.0003 | 0.0003 | 0.0957 | 0.7130 |
| C | 500 | 0.0000 | 0.0030 | 0.0010 | 0.1233 | 0.6300 |
| C | 1000 | 0.0000 | 0.0017 | 0.0007 | 0.0940 | 0.7140 |
| C | 2000 | 0.0000 | 0.0003 | 0.0003 | 0.0713 | 0.7770 |
| D | 500 | 0.0000 | 0.0017 | 0.0007 | 0.0913 | 0.7260 |
| D | 1000 | 0.0000 | 0.0017 | 0.0007 | 0.0720 | 0.7840 |
| D | 2000 | 0.0000 | 0.0003 | 0.0003 | 0.0470 | 0.8590 |
| D2 | 500 | 0.0000 | 0.0050 | 0.0013 | 0.1257 | 0.6230 |
| D2 | 1000 | 0.0000 | 0.0023 | 0.0009 | 0.1083 | 0.6750 |
| D2 | 2000 | 0.0000 | 0.0007 | 0.0005 | 0.0800 | 0.7600 |
| E | 500 | 0.0000 | 0.0000 | 0.0000 | 0.0090 | 0.9730 |
| E | 1000 | 0.0000 | 0.0000 | 0.0000 | 0.0027 | 0.9920 |
| E | 2000 | 0.0000 | 0.0000 | 0.0000 | 0.0020 | 0.9940 |
| F | 500 | 0.0000 | 0.0057 | 0.0014 | 0.1277 | 0.6170 |
| F | 1000 | 0.0000 | 0.0047 | 0.0012 | 0.1217 | 0.6350 |
| F | 2000 | 0.0000 | 0.0030 | 0.0010 | 0.1023 | 0.6930 |

Condition 1: largest design-set Type S rate is 0.0097 (A0w, T = 5), below 0.025.

Condition 2: A0 Type S 0.169 to 0.198 at every T; A1 above 0.05 at 7 of 9 settings (0.031 and 0.042 at 200 chips with tau 0.75 and 0.9). Best-model selection does not trigger the condition. Every conventional arm selects WC as best on OA in every replicate, and on macroF1 in 99.6% to 100%, more often than C at n = 500 (OA 1.000, macroF1 0.849).

Type S by pair (share of replicates with a significant wrong-sign McNemar call), computed from `results/full/mc/`. All conventional Type S decisions are on the DW vs IO pair:

| Arm | Budget | tau | DW vs IO | WC vs DW | WC vs IO |
| --- | --- | --- | --- | --- | --- |
| A0 | 5 / 10 / 20 | | 0.508 / 0.551 / 0.593 | 0 | 0 |
| A1 | 50 | 0.75 / 0.9 / 1.0 | 0.224 / 0.248 / 0.284 | 0 | 0 |
| A1 | 100 | 0.75 / 0.9 / 1.0 | 0.169 / 0.206 / 0.252 | 0 | 0 |
| A1 | 200 | 0.75 / 0.9 / 1.0 | 0.094 / 0.126 / 0.183 | 0 | 0 |

Real CVPR test split (20 MD + 20 DE tiles, 12,890,165 cells): A0 estimates DW - IO = -0.0010 with McNemar z = -11.5, a confident wrong sign. A0w on the same tiles estimates -0.0111 with SE 0.0215, not significant.

- Condition 1: met.
- Condition 2: met (Type S route).

Verdict: Supported.

Interpretation: Every conventional error is on the DW vs IO pair (true gap 0.006). Equal tiles per state over-weight Delaware about 5.4-fold, and IO is better than DW in Delaware. The pooled McNemar test then declares the wrong winner with high confidence, more often as more tiles are labelled. The design arms rarely make a confident call on this pair. They detect the true sign (DW > IO, significant) in only 5% to 18% of draws (C 0.052 to 0.104, D 0.081 to 0.175, D2 0.052 to 0.096, B2 0.111 to 0.152, A0w 0.058 to 0.094), and leave it unresolved otherwise. The data do not resolve a 0.006 gap at these budgets, and the design arms say so. On macroF1, A0 and A1 label 10^5 to 10^7 cells per draw (A1 1.7e5 to 7.3e5) against 500 to 2,000 for the element designs, so they find the clearly best model more reliably than C at n = 500. E labels the same 500 to 2,000 cells as D yet selects the best macroF1 model in every draw. That is because its bias inflates the gaps, not because it is more precise. Its mean estimated macroF1 gaps at n = 500 are 0.102, 0.156 and 0.054 (WC - DW, WC - IO, DW - IO) against true 0.055, 0.095 and 0.040; its OA gaps are 0.143, 0.180 and 0.036 against 0.081, 0.087 and 0.006.

### H4 Purity filtering

Criterion: "Supported if all hold: 1. B1(tau) OA bias against the full-population truth increases with tau (0.75 < 0.9 < 1.0) for every model, and B1(1.0) OA bias > max(2 MCSE, 0.01) for every model. 2. B1(tau) is consistent for its restricted truth: |mean B1(tau) - restricted truth(tau)| <= max(2 MCSE, 0.002) for OA. 3. B2 meets the H1 design-set criterion."

B1 OA bias against the full-population truth (all budgets, all models): tau 0.75: +0.048 to +0.051; tau 0.9: +0.076 to +0.078; tau 1.0: +0.099 to +0.108. Strictly increasing for all 9 (budget, model) combinations. At tau = 0 the bias is -0.001 to +0.002.

Against the restricted truths, max |bias| is 0.0015 over all taus, budgets and models; all within tolerance. At 50 chips all 12 biases are negative (-0.0004 to -0.0015), a small finite-sample effect.

B2 against the H1 design-set criterion: OA passes, but macroF1 fails at 50 chips (bias -0.006 to -0.007), at 100 chips for WC and IO, and at 200 chips for WC, and the class-level share is 0.822 < 0.95.

- Condition 1: met.
- Condition 2: met.
- Condition 3: not met.

Verdict: Criterion not met; labelled Partially supported (M6 convention). Conditions 1 and 2 hold; condition 3 fails.

Interpretation: The purity filter's effect on OA is large, monotone and similar across models (about +0.10 at tau = 1.0). On macroF1 it is unequal: A1 at tau = 1.0 inflates WC by +0.110 to +0.115 but IO by only +0.036 to +0.043, which widens the WC vs IO gap. Correct chip weights recover the restricted population to within 0.0015 but not the full population, because cells below the purity threshold have zero inclusion probability. Removing the filter and the complete-chip restriction (B2) removes the OA bias. B2 fails condition 3 for the same reason as the other design arms fail H1: macroF1 and rare-class bias at small chip budgets.

### H5 Efficiency of a shared sample

Criterion: "Supported if the median rho over (model, class) is <= 1.25 at n = 1000 and at n = 2000. Also report the maximum rho and the classes where D is weakest, and the cost ratio (F labels = 3 x D labels)."

| n | Median rho | Min | Max |
| --- | --- | --- | --- |
| 500 | 0.899 | 0.691 | 1.786 |
| 1000 | 0.921 | 0.702 | 2.065 |
| 2000 | 0.932 | 0.707 | 1.914 |

Weakest cases (largest rho): barren UA for WC (2.065 at n = 1000, 1.914 at n = 2000) and DW (1.779, 1.684). Cost ratio F / D = 3.

- Median rho <= 1.25 at n = 1000: met (0.921).
- Median rho <= 1.25 at n = 2000: met (0.932).

Verdict: Supported.

Interpretation: At the same labels per model, the shared consensus-stratified sample gives median UA/PA interval widths about 8% narrower than each model's own stratified sample, at one third of the total labels. The width comparison flatters D in its weakest cells, because D's SEs understate its variability there. For barren UA, D's SE ratio is 0.46 to 0.92 and its coverage 0.43 to 0.87, against 0.96 to 1.03 and 0.92 to 0.96 for F, and D's barren UA bias reaches +0.085 while F's is at most 0.003. Measured by empirical SD, F is up to 3.8 times more precise there (WC barren UA at n = 500: SD 0.266 under D vs 0.071 under F). The cause: a model's own barren predictions fall mostly outside the consensus barren strata (the other two models disagree), so D samples few of them. The criterion, defined on median rho, holds; the shared sample is not a substitute for per-model sampling of a model's rare classes.

### 3.7 Undefined rates (required by HYPOTHESES.md)

Share of replicates with an undefined estimate (zero denominator). Non-zero cases only; OA and area_c are never undefined.

| Arm | Budget | UA barren | PA barren | macroF1 |
| --- | --- | --- | --- | --- |
| C | 500 / 1000 / 2000 | 0.280-0.668 / 0.095-0.453 / 0.009-0.213 | 0.078 / 0.007 / 0 | 0.048-0.073 / 0.002-0.006 / 0 |
| D2 | 500 / 1000 / 2000 | 0.296-0.700 / 0.089-0.479 / 0.008-0.196 | 0.110 / 0.009 / 0 | 0.063-0.108 / 0.003-0.006 / 0 |
| A0, A0w | 5 | 0.018 (DW and IO) | 0 | 0 |
| A1, B1 | 50 / 100 | 0.028-0.030 / 0.001 | 0 | 0 |
| B2 | 50 | 0.007 | 0 | 0 |

Biases and coverages for these cells are conditional on the class appearing in the sample. In particular C's and D2's macroF1 bias and their macroF1 best-model probability (C 0.849 at n = 500) exclude the 5% to 11% of draws where barren is absent.

### H0 Honest null (reported, no pass or fail)

Share of replicates whose estimated ranking equals the true ranking, per metric (the label requires both metrics >= 0.95):

| Arm | Budget | tau | OA exact | macroF1 exact | Label |
| --- | --- | --- | --- | --- | --- |
| A0 | 5 / 10 / 20 | | 0.483 / 0.445 / 0.402 | 0.951 / 0.995 / 1.000 | |
| A1 | 50 | 0.75 / 0.9 / 1.0 | 0.748 / 0.726 / 0.679 | 0.973 / 0.978 / 0.975 | |
| A1 | 100 | 0.75 / 0.9 / 1.0 | 0.801 / 0.775 / 0.728 | 0.996 / 0.997 / 0.997 | |
| A1 | 200 | 0.75 / 0.9 / 1.0 | 0.886 / 0.858 / 0.794 | 1.000 / 1.000 / 1.000 | |
| E | 500 / 1000 / 2000 | | 0.973 / 0.992 / 0.994 | 0.996 / 1.000 / 1.000 | ranking robust, absolute values biased |

E, which analyses D's sample with equal weights, ranks the models correctly in 97% to 99% of draws while understating OA by 0.05 to 0.15. Here the ranking is right because the bias happens to preserve and widen the gaps, not because E is robust. Read per metric, every A0 and A1 setting is also "ranking robust, absolute values biased" for macroF1: macroF1 exact share >= 0.95 with macroF1 bias above 0.01 in all 36 cells. The macroF1 ranking (true gaps 0.041 and more) is robust for all conventional arms. The OA ranking (smallest gap 0.006) is not robust for A0 or A1.

## 4. Surprises and limitations

1. The design arms' macroF1 and rare-class estimates are biased at these budgets, so H1 condition 1, H2 condition 1 and H4 condition 3 fail. The pre-registered tolerances (0.002 for macroF1, 0.005 for UA/PA/area) are tight for statistics built from classes of 0.5% to 6% of the area at n = 500 to 2,000. reports/M3.md (committed before the freeze) predicted the rare-class UA/PA failure for D on dev. The macroF1 failure was not anticipated. It is the main weakness of the design-based case here.
2. A0w (correctly weighted tiles) removes A0's bias but under-covers at T = 5 to 20 tiles per state (0.83 to 0.93). With few PSUs, Wald intervals are too narrow. A t-based interval was considered and not adopted, to avoid tuning on dev results (DECISIONS.md entry 25).
3. Conventional arms label far more cells (an A0 draw labels 3.1 million cells at T = 5 and 12.5 million at T = 20). On the clearly separated pairs they rank as well as or better than the design arms. Their failure is confined to the close pair, and the danger is confidence: a 0.17 to 0.20 rate of significant wrong-sign calls.
4. Dynamic World and Esri/IO map whole suburbs as "built area", which the protocol crosswalk maps to impervious. Their impervious UA (0.40, 0.31) and low-vegetation PA (0.60, 0.69) reflect this class-definition mismatch as much as mapping skill. It affects all arms equally and does not change arm comparisons.
5. Two WorldCover tiles north of 39 N have a sub-cell north-south offset; the map was kept as published (DECISIONS.md entry 26).
6. The reference itself has errors (user's accuracy of barren 63% in the 2021/22 accuracy assessment, Table 2 of the LULC User Guide 2024 Edition, ScienceBase item 66d099c9d34e98e8a924e574). It is treated as truth by construction, which affects all arms equally.
7. Only three models, one region and one year. The DW vs IO result rests on one close pair.
8. Bootstrap SEs (macroF1, F1, IoU) exist only for replicates 0 to 199. No hypothesis criterion uses them, but their coverage is poor in several design arms (macroF1, n_se = 183 to 200):

| Arm | Budget | macroF1 coverage | SE ratio |
| --- | --- | --- | --- |
| C | 500 / 1000 / 2000 | 0.43-0.52 / 0.52-0.76 / 0.68-0.91 | 0.51-0.61 / 0.66-0.81 / 0.79-0.95 |
| D2 | 500 / 1000 / 2000 | 0.40-0.53 / 0.46-0.73 / 0.67-0.85 | 0.52-0.60 / 0.59-0.77 / 0.79-0.93 |
| A0w | 5 / 10 / 20 | 0.67-0.71 / 0.70-0.72 / 0.76-0.78 | 0.75-0.84 / 0.77-0.81 / 0.75-0.82 |
| B2 | 50 / 100 / 200 | 0.86-0.90 / 0.91-0.93 / 0.91-0.93 | 0.88-0.92 / 0.91-0.95 / 0.96-0.99 |
| D | 500 / 1000 / 2000 | 0.89-0.90 / 0.94-0.96 / 0.92-0.97 | 0.89-0.96 / 0.94-0.95 / 0.99-1.03 |
| F | 500 / 1000 / 2000 | 0.84-0.88 / 0.89-0.98 / 0.96-0.98 | 0.87-0.89 / 0.94-1.06 / 0.99-1.04 |

The macroF1 pairwise decisions in ranking_summary rely on these intervals. In C and D2 at small n they are too narrow, because rare-class F1 is nearly undefined in many draws. D, which oversamples rare-class strata, is close to nominal from n = 1000.
9. Full tables required by HYPOTHESES.md (bias for every arm and every parameter, including UA_c, PA_c, area_c, B1 macroF1 and the restricted scopes): `results/full/tables/supp_estimates_summary.csv` (Table S1) and `results/full/tables/table2_bias_rmse_coverage.csv` (Table 2).

## 5. Reproducibility

| Item | Value |
| --- | --- |
| Code commit for the full run | 0ce449d (freeze record) on top of 9eaa7db |
| HYPOTHESES.md SHA-256 | 7cba572b17ce2618110cec61be3c81b03fff97edaf553b500d079c0d7de12e75 (unchanged after the run) |
| Base seed | 20261115; SeedSequence spawn per (arm, budget), then per replicate; seed stored in every row |
| Replicates | 1,000 per (arm, budget); bootstrap subset 200, B = 200 |
| Monte Carlo wall time | about 10 minutes on 10 workers (per-arm times in reports/M5.md) |
| Data | Chesapeake LULC 2024 edition (DOI 10.5066/P14BEBRC), 2021/22 county rasters; ESA WorldCover 2021 v200; Dynamic World V1 (Earth Engine, annual mode of label over 2021); Esri/IO 10m Annual LULC v02 2021; Census 2021 cartographic boundaries; EPA L3 ecoregions; CVPR 2019 Chesapeake spatial index |
| Deviations | docs/DECISIONS.md entries 15 to 27 |
| Summaries | results/full/summary/*.csv; tables in results/full/tables/; figures in results/figures/ and reports/figures/ |


## 6. Adversarial review

A fresh subagent that had not seen the analysis received RESULTS.md, HYPOTHESES.md and the summary data. It recomputed every condition and spot-checked 26 numbers. All five verdicts follow mechanically from the criteria, and per-arm vs pooled readings of the design-set conditions change no verdict. Its spot checks matched for 25 numbers; the barren user's accuracy of 63% had no source in the repo. Findings and fixes:

| # | Finding | Fix |
| --- | --- | --- |
| 1 | The summary omitted A0w's OA under-coverage (0.83 to 0.93), the main reason H2 condition 1a fails. | Added to section 1. |
| 2 | Bootstrap macroF1 coverage was computed but described as "not evaluated"; it is poor in C, D2 and A0w. | Table added (section 4 item 8). |
| 3 | Undefined rates were not reported; the R_def rule drops the hardest barren cells from C and D2. | Section 3.7 added; footnote in H1. |
| 4 | H5 overclaimed: D's barren UA SEs understate its variability (SE ratio 0.46 to 0.92, coverage 0.43 to 0.87); by empirical SD F is up to 3.8 times more precise. | H5 interpretation and summary rewritten. |
| 5 | "Partially supported" softens criteria that require all conditions to hold. | Verdicts now say "criterion not met", with the M6 label in parentheses. |
| 6 | The full bias table and the SE ratio for every arm were missing. | SE ratio table added (H2); full tables linked (section 4 item 9). |
| 7 | False claim that DECISIONS.md predicted the failure before the freeze. | Corrected: reports/M3.md predicted the rare-class failure; macroF1 was not anticipated. |
| 8 | A0's DW OA bias at T = 20 (-0.00999) does not exceed the tolerance; A0's macroF1 bias equals A0w's and is not a protocol effect. | H1 condition 2 rewritten; it rests on A1 and E. |
| 9 | The wrong explanation for E's ranking success (cell counts); it comes from bias inflating the gaps. | H3 and H0 text corrected. |
| 10 | "Recovers exactly" overclaimed B1's restricted consistency. | "within 0.0015", with the negative bias at 50 chips noted. |
| 11 | The purity effect mixed the A1 and B1 ranges. | Both ranges given. |
| 12 | The H0 heading said "both"; the per-metric macroF1 label was missing. | Heading and text corrected. |
| 13 | Minor omissions: A0w fails in all classes; B2 impervious; F barren PA bias; boundary passes. | Added. |
| 14 | Design-arm power on the DW vs IO pair was not quantified; the macroF1 purity effect is unequal across models. | Added (5% to 18% detection, computed per pair from the raw replicates; macroF1 effect +0.11 WC vs +0.04 IO). |
| 15 | The 63% barren user's accuracy had no source. | Source cited (User Guide Table 2). |

The reviewer's power figures were derived from the all-pairs share. I recomputed them per pair from `results/full/mc/` before using them. They agree for D at n = 2000 (0.175) and differ slightly elsewhere; the per-pair values are reported.
