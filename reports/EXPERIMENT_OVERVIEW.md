# Experiment overview: design-based vs conventional benchmarking of land cover maps

This document explains the whole pilot in one place: the question, the data, every experiment, every assumption, and the results. It is written for a reader who has not followed the development. Detailed evidence lives in the milestone reports (`reports/M0.md` to `reports/M6.md`), the decision log (`docs/DECISIONS.md`) and the results document (`reports/RESULTS.md`). Numbers here are copied from those files.

Date: 2026-11-15. Repository: HamedAlemo/design-based-benchmarking-demo, branch `main`.

## Contents

1. The question
2. Why the truth is known
3. Data and population
4. Classes and crosswalks
5. Models evaluated
6. Sampling frames and strata
7. The ten sampling arms
8. Estimators
9. Validation experiments (before any Monte Carlo)
10. The Monte Carlo experiment
11. Pre-registered hypotheses
12. Results
13. Assumptions
14. Deviations and decisions made during the work
15. Limitations
16. Reproducibility and file map

## 1. The question

GeoAI benchmarks usually score a model on a test set built for convenience: a few clustered image tiles, chips balanced across rare classes, or only "pure" pixels. The score is then averaged over pooled pixels with no weights. Every such score estimates some population quantity, but the population is implicit and usually not the map's real area.

The pilot asks two things:

1. How far do conventional benchmark protocols drift from a map's true accuracy and from the true ranking of models?
2. Does a shared probability sample with known inclusion probabilities, analysed with design-based estimators, recover both?

## 2. Why the truth is known

The reference is a wall-to-wall 1 m land cover map of Maryland and Delaware. Every 10 m cell in the study area has a reference label, so the true accuracy of each model is computed exactly from all cells. Every sampling protocol is then simulated 1,000 times against this known truth. Bias, interval coverage and ranking errors are measured, not argued.

The reference is treated as truth by construction. Its own errors (Section 15) affect all protocols equally, so they do not change the comparison between protocols.

## 3. Data and population

### 3.1 Sources

| Data | Version | Use |
| --- | --- | --- |
| Chesapeake Bay Land Use/Land Cover Database, 2024 edition (DOI 10.5066/P14BEBRC) | 2021/22 county rasters, 1 m | Reference |
| ESA WorldCover | 2021 v200 | Model WC |
| Google Dynamic World V1 | Annual mode of the `label` band over 2021 (Earth Engine) | Model DW |
| Esri / Impact Observatory 10m Annual LULC | v02, 2021 | Model IO |
| Census cartographic boundaries | 2021, 1:500k, clipped to shoreline | State polygons |
| EPA Level III ecoregions | `us_eco_l3` | Strata for arm D2 |
| CVPR 2019 Chesapeake land cover spatial index | MD and DE 2013 tiles | The real benchmark's tile geometry and test split |

### 3.2 Analysis grid

- CRS: EPSG:5070 (CONUS Albers equal area), so every cell has the same area and class proportions are area proportions.
- Cells: 10 m, with edges on multiples of 10 m. The grid origin is snapped to multiples of 640 m so that 640 m chips nest exactly.
- The reference is in ESRI:102039, which pyproj confirms is identical to EPSG:5070, on integer-metre 1 m pixels. Each 10 m cell is therefore exactly 10 x 10 reference pixels; no warping was needed.
- Model maps are reprojected to the grid by nearest neighbour.

### 3.3 Population definition

A 10 m cell belongs to the population U if:

1. its centre lies inside Maryland or Delaware (Census 2021 cartographic boundaries), and
2. all 100 of its 1 m reference pixels are valid.

Open bay and ocean water lie outside the cartographic boundary and are excluded. Cells with incomplete reference are excluded, never imputed. The population was fixed once (milestone M2) and never redefined.

| Extent | Grid (cells) | N (population cells) | MD | DE | Excluded for incomplete reference |
| --- | --- | --- | --- | --- | --- |
| Dev (35 km x 33 km test area across the MD-DE border) | 4,160 x 4,032 | 11,540,200 | 6,166,013 | 5,374,187 | 0 |
| Full (all of MD and DE) | 40,064 x 21,824 | 318,425,338 | 266,353,825 | 52,071,513 | 103,018 |

The dev extent was used to build and test everything cheaply. Only the full extent produces evidence.

### 3.4 Per-cell reference attributes

For each cell: the plurality class of its 100 harmonized pixels (ties go to the lower class code; 665,062 tied cells on the full extent), the purity (the plurality count, 20 to 100), the five class counts, the state, the ecoregion, the tile and chip it belongs to, and its stratum in each stratified design.

## 4. Classes and crosswalks

### 4.1 Harmonized classes

| Code | Class | Notes |
| --- | --- | --- |
| 0 | No prediction | Model maps only: nodata, cloud, snow. Always counts as wrong. |
| 1 | Water | |
| 2 | Tree canopy | Includes tree canopy over roads, structures and other impervious surfaces |
| 3 | Low vegetation | Includes scrub/shrub and emergent wetlands |
| 4 | Barren | |
| 5 | Impervious | Structures, roads, other impervious |

### 4.2 Reference crosswalk

The 2024 edition has no separate land cover raster. Its 56-class land use/land cover (LULC) raster comes with an official crosswalk that gives each LULC code a land cover parent. Each parent was mapped to the harmonized classes by name. Two cases went to the PI:

- "Shrubland" is the 2024 name for the 2022 class "Scrub/Shrub"; mapped to 3.
- LULC 75, "Tidal Wetlands Harvested Forest", has two listed parents ("Low Vegetation; Barren"); mapped to 3, like the matching riverine and terrene codes. It covers 1,054,074 pixels on the full extent (0.002% of valid pixels).

### 4.3 Model crosswalks

| Model | Mapping to harmonized classes |
| --- | --- |
| WorldCover | tree 10 to 2; shrub 20, grass 30, crop 40, herbaceous wetland 90 to 3; built-up 50 to 5; bare 60 to 4; water 80 to 1; snow 70 and nodata to 0 |
| Dynamic World | water 0 to 1; trees 1 to 2; grass 2, flooded vegetation 3, crops 4, shrub 5 to 3; built 6 to 5; bare 7 to 4; snow 8 and no observation to 0 |
| Esri/IO | water 1 to 1; trees 2 to 2; flooded vegetation 4, crops 5, rangeland 11 to 3; built area 7 to 5; bare 8 to 4; snow 9, clouds 10 and nodata to 0 |

Class 0 is rare: WC 0.0000%, DW 0.0073%, IO 0.00003% of population cells.

## 5. Models evaluated

Three existing 2021 maps act as three "models". Their true accuracy over the full population:

| Metric | WC | DW | IO |
| --- | --- | --- | --- |
| OA | 0.8528 | 0.7720 | 0.7662 |
| macroF1 | 0.7279 | 0.6731 | 0.6326 |
| mIoU | 0.6088 | 0.5397 | 0.5115 |
| OA, Maryland | 0.8531 | 0.7772 | 0.7665 |
| OA, Delaware | 0.8508 | 0.7455 | 0.7647 |

WorldCover is clearly best. Dynamic World and Esri/IO differ by only 0.006 in OA, and the order reverses by state: DW leads in Maryland, IO in Delaware. This close pair is what makes the ranking test sharp.

Reference area shares: water 0.0575, tree 0.4520, low vegetation 0.4126, barren 0.0051, impervious 0.0729.

## 6. Sampling frames and strata

### 6.1 Tile frame (arms A0, A0w)

The CVPR 2019 benchmark used USGS quarter-quadrangle tiles (0.0625 degrees in NAD83). The frame is the full quarter-quadrangle grid over the population. A cell belongs to the tile containing its centre, computed exactly from the cell centre's NAD83 longitude and latitude. A tile's stratum is the state holding most of its cells.

| Extent | Tiles | MD | DE |
| --- | --- | --- | --- |
| Dev | 48 | 24 | 24 |
| Full | 1,045 | 881 | 164 |

All 232 MD and DE CVPR tiles matched a frame tile (IoU 0.815 to 0.83; CVPR tiles are slightly debuffered). The real CVPR test split is 20 MD + 20 DE tiles.

Because Delaware has 164 tiles and Maryland 881, drawing the same number of tiles per state gives each Delaware cell about 5.4 times the weight its population share warrants, if the cells are pooled without weights.

### 6.2 Chip frame (arms A1, B1, B2)

Chips are 64 x 64 cells (640 m). A chip is complete if all 4,096 cells are in the population. Each chip gets a rare-class tag: the rarest class (by population share) covering at least 5% of the chip's cells. Rarity order on the full extent, rarest first: barren, water, impervious, low vegetation, tree.

| Tag | Complete chips | All chips |
| --- | --- | --- |
| Water | 9,800 | 13,083 |
| Tree canopy | 5,535 | 5,744 |
| Low vegetation | 36,133 | 36,999 |
| Barren | 1,471 | 1,905 |
| Impervious | 22,252 | 22,666 |
| Total | 75,191 | 80,397 |

Purity filters keep only cells whose plurality covers at least tau of the 100 pixels. Scored cells on the full extent: tau 0.75, 281.3 million; tau 0.9, 260.3 million; tau 1.0, 239.7 million (75.3% of N).

### 6.3 Strata for the stratified designs

| Design | Strata | Full-extent count | Allocation |
| --- | --- | --- | --- |
| D | Product agreement: the consensus class (at least 2 of 3 maps agree on a non-zero class) crossed with the level (3 of 3, 2 of 3), plus one "no majority" stratum | 11 | At least min(50, floor(n / 2H)) per stratum; the rest by Neyman allocation with assumed error rates 0.05 (3 of 3), 0.40 (2 of 3), 0.60 (no majority) |
| D2 | State x EPA Level III ecoregion; strata under 0.5% of N merge into a per-state "other" | 10 | At least min(30, floor(n / 2H)); the rest proportional to N_h |
| F | Each model's own map classes (one independent sample per model) | 5 or 6 per model | At least min(50, floor(n / 2H)); the rest proportional to N_h |

All allocations use largest-remainder rounding and are capped at N_h, with excess redistributed.

## 7. The ten sampling arms

Each arm is a sampling protocol plus an estimator. Arms marked "reuses" analyse another arm's draw, so the comparison between them is paired.

| Arm | Group | Selection | Estimator | Budgets per draw | What it represents |
| --- | --- | --- | --- | --- | --- |
| A0 | Conventional | Simple random sample of T tiles per state; all cells scored | Naive: unweighted pooled pixels, binomial SE, McNemar test for pairs | T = 5, 10, 20 per state | The CVPR-style tile benchmark |
| A0w | Repair | Reuses A0's draw | Design-based: weights M_s / T, stratified one-stage cluster variance | as A0 | A0 analysed correctly |
| A1 | Conventional | Complete chips only, an equal number per rare-class tag; only cells with purity at least tau are scored | Naive pooled; also chip-averaged mIoU | 50, 100, 200 chips; tau = 0.75, 0.9, 1.0 | A class-balanced, purity-filtered chip benchmark |
| B1 | Restricted | Reuses A1's draw | Design-based with correct chip weights; purity filter kept | as A1; tau = 0, 0.75, 0.9, 1.0 | A1 weighted correctly; it targets a restricted population |
| B2 | Repair | All chips with any population cell, an equal number per tag; no purity filter | Design-based cluster | 50, 100, 200 chips | Chip sampling done correctly |
| C | Design | Simple random sample of cells | Design-based element | n = 500, 1000, 2000 | The simplest probability sample |
| D | Design | Stratified by product agreement | Design-based element (Stehman 2014) | n = 500, 1000, 2000 | A shared, model-agnostic stratified sample |
| D2 | Design | Stratified by state x ecoregion | Design-based element | n = 500, 1000, 2000 | A geographic stratified sample |
| E | Mistake | Reuses D's draw | Naive: equal weights, binomial SE, McNemar | as D | A stratified sample analysed as if it were simple random |
| F | Per-model reference | Per model, stratified by that model's own classes | Design-based element | n per model (total 3n) | The classic per-map accuracy assessment |

The decomposition chain is A1 to B1(tau) (removes class balancing), B1(tau) to B1(0) (removes the purity filter), B1(0) to B2 (removes the complete-chip restriction). A0 to A0w separates "ignoring inclusion probabilities" from "the sample itself".

On dev, A0 used T = 2, 3, 5 tiles per state, because the dev frame has only 24 tiles per state.

## 8. Estimators

### 8.1 Parameters

For each model: overall accuracy (OA); user's accuracy (UA_c), producer's accuracy (PA_c), F1_c and IoU_c for each class; macroF1 and mIoU (plain means over the five classes); and the reference area share of each class (area_c). OA, UA, PA and area are ratios of totals. F1, IoU, macroF1 and mIoU are nonlinear. A ratio with a zero denominator is undefined (NaN), never 0, and is counted in R_def, the number of replicates where an estimate exists.

### 8.2 Design-based estimators

- Design weight w = 1 / pi for every sampled unit; in cluster designs the PSU's weight applies to each of its cells.
- Point estimates are ratios of weighted totals (Hajek form). The same coefficient matrices define a parameter at the cell level, the PSU level and the population level, so truth and estimates use identical definitions.
- Variance, stratified element designs: V = sum over strata of N_h^2 (1 - n_h/N_h) s2_h / n_h, with s2_h the variance of the linearized residuals z = (y - R x) / X_hat.
- Variance, stratified one-stage cluster designs: the same formula over PSU totals (M_h, m_h).
- Nonlinear parameters: Rao-Wu rescaling bootstrap within strata, B = 200 on replicates 0 to 199, including the finite population correction.
- Paired comparison of two models: d = 1[model k right] - 1[model l right], estimated as a ratio with the same design variance. A decision is significant if the 95% interval excludes 0.
- Intervals: Wald 95%.
- Secondary: per-state domain estimates and a model-assisted (post-stratified) area estimator for arm D.

### 8.3 Naive estimators, as practiced

Unweighted pooled counts. Binomial SE sqrt(p(1-p)/n) for OA, UA and PA, where n is the relevant pixel count. No SE for F1, IoU, macroF1 or mIoU. Pairwise test: McNemar z on pooled pixels, treated as independent.

## 9. Validation experiments (before any Monte Carlo)

### 9.1 Estimators (milestone M3)

| Experiment | Result |
| --- | --- |
| Hand-worked unit tests (an 8-cell, 2-stratum element sample; a 5-PSU, 2-stratum cluster sample; area estimator) | All match hand calculations |
| Synthetic element population (20,000 cells, 4 strata, a 2% rare class), 20,000 draws at n = 500 and 2,000 | OA bias within MCSE; variance ratio 0.99 to 1.00; coverage 0.947 to 0.950 at n = 2,000 |
| Synthetic cluster population (300 PSUs with intra-cluster correlation), 20,000 draws at 40 and 80 PSUs | Coverage 0.936 to 0.940 at 80 PSUs, 0.916 to 0.924 at 40. Naive pooled SE covers only 0.33 to 0.37, showing the test can detect the failure. |
| Comparison with the R `survey` package (svyratio) | Estimates and SEs agree to 3e-14 relative |
| Bootstrap vs linearization | Mean bootstrap SE / linearized SE 0.996 to 0.999 |
| Speed | One full estimate set: 7.6 ms (element, n = 2,000), 2.8 ms (cluster, 200 PSUs) |
| Real-data check on dev, 5,000 draws | D at n = 1,000: OA bias within 1 MCSE, coverage 0.941 to 0.945. A0w at T = 5: OA bias within 3 MCSE, coverage 0.901 to 0.908 (recorded as a finding) |

Ratio estimators are consistent but not unbiased. The synthetic UA bias at small cluster samples (about -0.001) and the large rare-class UA/PA bias of D on dev (barren PA +0.044, barren UA up to +0.070) both match the analytic second-order ratio bias. They are properties of the estimator, not code errors.

### 9.2 Samplers (milestone M4)

Every element draw has exactly n cells and the planned stratum sizes. Weights sum to N (element) or M_h (cluster). PSUs are selected with their stated probabilities (Bonferroni-limited z-scores over 20,000 draws; per-stratum SD of z within a chi-square band). Selection within strata is uniform (chi-square p from 0.096 to 0.91). Paired arms share their draw. The same seed gives identical samples. A1 never selects an incomplete chip. One draw plus data gather takes 0.2 to 4.0 ms on the full extent.

## 10. The Monte Carlo experiment

| Setting | Value |
| --- | --- |
| Replicates | 1,000 per (arm, budget); 50 on dev (smoke test only) |
| Bootstrap | Replicates 0 to 199, B = 200 |
| Seeds | numpy PCG64 through SeedSequence(20261115): one child per (arm, budget), then one per replicate. Each replicate's integer seed is stored in its rows. |
| Pairing | A0w uses A0's draw, B1 uses A1's, E uses D's |
| Output | 45 files, 5,022,000 estimate rows |
| Run time | About 10 minutes on 10 worker processes |
| Reproducibility check | Two (arm, budget) combinations rerun from scratch gave identical results |

Summaries per arm, budget, model and parameter: bias, relative bias, Monte Carlo SE of the bias, RMSE, empirical SD, mean estimated SE, SE ratio, 95% interval coverage, mean interval width and undefined rate. Ranking summaries: probability of picking the truly best model, Kendall tau, the share of exactly correct rankings, and pairwise decision classes (correct and significant, not significant, Type S = significant with the wrong sign).

## 11. Pre-registered hypotheses

`docs/HYPOTHESES.md` was frozen before any full-extent replicate was run (commit 9eaa7db, SHA-256 7cba572b...7e75), and was never edited. Each hypothesis is supported only if all its conditions hold.

| Hypothesis | Claim | Conditions, in short |
| --- | --- | --- |
| H1 Bias | Conventional arms are biased; design arms are not | 1: design arms unbiased for OA and macroF1 (within max(2 MCSE, 0.002)) and for 95% of class-level UA/PA/area cells (within max(2 MCSE, 0.005)). 2: some conventional arm biased by more than 0.01. |
| H2 Uncertainty | Naive SEs under-cover; design SEs reach nominal coverage | 1: design OA coverage in [0.93, 0.97]; UA/PA coverage >= 0.90 for 90% of cells. 2: A0 OA coverage < 0.90 at every T for at least two models. |
| H3 Ranking | Design arms rarely make confident wrong comparisons; conventional arms can | 1: design Type S rate for OA pairs <= 0.025 + 2 MCSE. 2: some conventional arm with Type S > 0.05, or a best-model rate at least 0.10 below arm C at n = 500. |
| H4 Purity filtering | Purity filtering inflates accuracy and weighting cannot repair it | 1: B1 bias rises with tau and exceeds 0.01 at tau = 1. 2: B1 consistent for its restricted population. 3: B2 meets the H1 design criterion. |
| H5 Efficiency | One shared sample (D) gives per-model precision close to per-model samples (F) at one third of the cost | Median ratio of CI widths (D / F) <= 1.25 at n = 1,000 and 2,000. |
| H0 Honest null | Reported, no pass or fail | Share of conventional replicates with the correct ranking; label cases "ranking robust, absolute values biased". |

The design set is C, D, D2, F, A0w and B2; the conventional set is A0, A1 and E. Design-set conditions were applied to each design arm separately; a pooled reading changes no verdict.

## 12. Results

### 12.1 Verdicts

| Hypothesis | Verdict | Deciding numbers |
| --- | --- | --- |
| H1 | Criterion not met (labelled "partially supported") | Design-arm OA bias at most 0.0023 at every budget. But macroF1 is biased in every design arm at small samples (48 of 54 cells fail; up to -0.034 for A0w, -0.020 for D2, +0.021 for F), and rare-class UA/PA bias fails the 95% rule in A0w, B2, D and F. Condition 2 holds: A1 is biased by +0.036 to +0.094, E by -0.053 to -0.149. |
| H2 | Criterion not met ("partially supported") | A0 OA coverage 0.005 to 0.016 (condition 2 holds). Condition 1 fails: A0w OA coverage 0.829 to 0.926, B2 at 100 chips 0.921 to 0.931, and UA/PA coverage >= 0.90 holds for 90% of cells only in F. C, D, D2 and F have OA coverage 0.933 to 0.960. |
| H3 | Supported | Design-arm Type S at most 0.0097. A0 Type S 0.169 to 0.198, all on the DW vs IO pair, where A0 is confidently wrong in 51% to 59% of draws. A1 0.031 to 0.095. |
| H4 | Criterion not met ("partially supported") | B1 OA bias against the full truth: +0.048 to +0.051 (tau 0.75), +0.076 to +0.078 (0.9), +0.099 to +0.108 (1.0), rising for every model. Against its restricted truth, at most 0.0015. Condition 3 fails because B2 inherits the macroF1 and rare-class problems. |
| H5 | Supported | Median rho 0.899 (n = 500), 0.921 (1,000), 0.932 (2,000). Worst: barren UA, rho up to 2.07; by empirical SD, F is up to 3.8 times more precise there. |

### 12.2 What the results show

1. Ignoring inclusion probabilities produced confident wrong rankings. A0 over-weights Delaware about 5.4-fold, IO beats DW in Delaware, and the pooled McNemar test treats millions of clustered pixels as independent (SE ratio 0.006 to 0.009). It therefore declared IO better than DW, significantly, in most draws, and more often with more tiles (Type S 0.169 at T = 5, 0.198 at T = 20).
2. The real CVPR test split repeats this. Its pooled score ranks IO above DW with McNemar z = -11.5. The weighted estimate on the same tiles gives -0.011 with SE 0.022: not significant, which is the honest answer for a 0.006 gap.
3. Purity filtering inflates OA by about 0.10 at tau = 1.0 for every model, and correct weighting cannot remove it, because the excluded cells have zero inclusion probability.
4. Analysing a stratified sample as if it were simple random (E) understated OA by 0.05 to 0.15, yet ranked the models correctly in 97% to 99% of draws. A ranking can be right while every absolute number is wrong.
5. Design-based estimation is unbiased and well calibrated for OA at 500 to 2,000 labels. For nonlinear metrics (macroF1) and rare classes (barren is 0.5% of the area) at these budgets, it carries real small-sample bias, and its Wald and bootstrap intervals under-cover (macroF1 bootstrap coverage 0.40 to 0.53 for C and D2 at n = 500). This is the main weakness of the design-based case and the main reason three of the five hypotheses fail their pre-registered criteria.
6. On the DW vs IO pair, design arms make a correct significant call in only 5% to 18% of draws. They mostly report "not resolved" rather than a wrong answer.

The milestone verdicts, tables and the adversarial review are in `reports/RESULTS.md`. Figures are in `reports/figures/` (`fig1` to `fig6`, suffix `_full`).

## 13. Assumptions

### 13.1 About the truth and the population

| # | Assumption | Why | If it is wrong |
| --- | --- | --- | --- |
| 1 | The Chesapeake 1 m map is the truth. | It is the only wall-to-wall reference; its own accuracy is high (95% overall for five classes). | Absolute accuracies shift, but every arm faces the same truth, so arm comparisons hold. |
| 2 | The 10 m reference class is the plurality of 100 harmonized pixels, ties to the lower code. | Deterministic and standard. | Mixed cells (purity < 100) have a debatable "true" class; the purity filter experiments show how much this matters (up to 0.10 OA). |
| 3 | The population is cells inside the cartographic state boundary with complete reference. | Excludes open water that would inflate accuracy; no imputation. | A different boundary changes the truth and the water share, not the method comparison. |
| 4 | Equal-area cells in EPSG:5070. | Makes class shares area shares. | Not applicable; verified. |

### 13.2 About the models

| # | Assumption | Why | If it is wrong |
| --- | --- | --- | --- |
| 5 | The three published 2021 maps stand in for three models. | Real maps with real error structures, no training needed. | Only three models and one close pair; results on ranking rest on that pair. |
| 6 | The crosswalks in Section 4.3, with "built area" mapped to impervious. | Protocol choice. | DW and IO label whole suburbs "built", so their impervious UA (0.40, 0.31) and low-vegetation PA reflect class definitions as much as skill. All arms see the same maps. |
| 7 | Dynamic World's annual summary is the mode of `label` over 2021. | Simple, standard, reproducible. | Another summary would change DW's accuracy, not the design comparison. |
| 8 | Nodata, cloud and snow count as wrong (class 0). | Dropping them would hide a real failure. | Negligible here (at most 0.0073% of cells). |
| 9 | Maps are used as published, including a sub-cell north-south offset in WorldCover's tiles north of 39 N. | Shifting would alter the model. | WC's true accuracy there is slightly lower than with perfect registration; the truth includes it. |

### 13.3 About sampling and estimation

| # | Assumption | Why | If it is wrong |
| --- | --- | --- | --- |
| 10 | Selection is without replacement inside strata, with exactly known inclusion probabilities. | This is the design-based setting being tested. | Verified by the M4 checks. |
| 11 | Wald 95% intervals for all ratio parameters. | Protocol choice, fixed before results. | They under-cover with few PSUs (A0w) and for rare classes; t-based or logit intervals were not adopted, to avoid tuning to dev results. |
| 12 | Hajek ratio estimators. | Standard (Stehman 2014); valid when strata differ from map classes. | They are consistent, not unbiased; small-sample bias is visible for rare classes and was reported, not corrected. |
| 13 | macroF1 is the plain mean over the five classes and is undefined if any class F1 is undefined. | A strict definition; no silent dropping of classes. | At small n, macroF1 is undefined in 5% to 11% of C and D2 draws, and its reported bias is conditional on barren appearing. |
| 14 | The D strata use the three maps being evaluated. | Valid, because strata are fixed before sampling. | None for validity. It makes D weak for one model's rare-class UA where the other two disagree (H5's worst case). |
| 15 | Cells outside every ecoregion polygon form their own D2 group per state. | The protocol is silent; this keeps every cell in exactly one stratum. | None for validity. |
| 16 | The real CVPR test split is evaluated with pi = 20 / M_s. | Documentation only; the real split was drawn from the CVPR frame, not ours. | Its A0w interval is indicative, not a design-based result. |

### 13.4 About the experiment

| # | Assumption | Why | If it is wrong |
| --- | --- | --- | --- |
| 17 | 1,000 replicates are enough. | MCSE of a coverage near 0.95 is about 0.007; of a Type S rate near 0.02 about 0.0025. | Borderline cases are flagged as fragile (for example F's 0.900 share in H2, B2's 0.970 coverage). |
| 18 | Dev results never tune the method or the criteria. | Prevents fitting the protocol to the answer. | Not applicable; all criteria changes were approved by the PI before the freeze and are logged. |

## 14. Deviations and decisions made during the work

All are logged in `docs/DECISIONS.md` with date, reason and expected effect. Decisions approved by the PI in chat are marked.

| Entry | Decision |
| --- | --- |
| 15 | Harmonized classes derived from the release's own LULC crosswalk (no separate land cover raster exists). |
| 16, 17 | Shrubland mapped to 3; LULC 75 mapped to 3 (PI). |
| 18 | Class names matched case-insensitively. |
| 19 | Reference files downloaded from the public ScienceBase S3 bucket (same files). |
| 20 | Rao-Wu bootstrap with the finite population correction; without it, cluster SEs were overstated by about 17%. |
| 21 | Grid origin snapped to 640 m multiples. |
| 22, 23 | M3 synthetic bias test judged against the predicted second-order ratio bias, with a Bonferroni limit across about 190 cells (PI). |
| 24 | M4 uniformity test uses a Bonferroni limit across PSUs, plus a per-stratum SD check (PI). |
| 25 | A0w under-coverage at small T recorded as a finding; Wald intervals kept (PI). |
| 26 | WorldCover kept as published despite the north-tile offset (PI). |
| 27 | No-ecoregion cells grouped per state in D2. |

## 15. Limitations

1. One region, one year, three models. The ranking result rests on a single close pair (DW vs IO).
2. The reference has its own errors (barren user's accuracy 63% in its 2021/22 accuracy assessment, LULC User Guide 2024 Edition, Table 2). They affect all arms equally.
3. Budgets of 500 to 2,000 labels are small for rare classes. Design-based macroF1 and rare-class estimates are biased at these budgets, and their intervals under-cover. Larger budgets or other interval methods were not tested.
4. Conventional arms label 10^5 to 10^7 cells per draw against 500 to 2,000 for the element designs. On clearly separated models they rank as well as or better than the design arms. Their failure is confined to close pairs, and the danger is false confidence.
5. Wald intervals with few PSUs (A0w at 5 to 20 tiles per state) under-cover. A t-based interval would probably help but was not tested on the final data.
6. The crosswalk's treatment of "built area" as impervious penalizes DW and IO on impervious and low vegetation.
7. Foundation-model probe maps (milestone M7) were not run.

## 16. Reproducibility and file map

### 16.1 How to rerun

```bash
conda activate bowpilot
bowpilot data --extent full
bowpilot population --extent full
bowpilot validate-estimators --extent dev
bowpilot validate-sampling --extent dev
bowpilot montecarlo --extent full --jobs 10
bowpilot report --extent full
```

Dynamic World needs Earth Engine credentials and a Cloud project id in `config/products.yaml`.

### 16.2 Where things are

| Path | Contents |
| --- | --- |
| `docs/PROTOCOL.md`, `docs/HYPOTHESES.md` | The protocol and the frozen criteria |
| `docs/DECISIONS.md` | Every deviation and decision |
| `config/` | Classes, crosswalks, products, frames, arms, Monte Carlo settings |
| `src/bowpilot/` | All code: data, population, estimation, sampling, simulate, report, validation |
| `tests/` | 50 tests: estimators (hand-worked, synthetic, R cross-check, speed), population, sampling, Monte Carlo, report |
| `reports/M0.md` to `reports/M6.md` | Milestone reports with every acceptance check |
| `reports/RESULTS.md` | Verdicts, deciding tables and the adversarial review |
| `reports/figures/` | QA quicklooks and the six paper figures |
| `results/full/summary/*.csv`, `results/full/tables/` | Summary tables (Table 1, Table 2, supplementary tables) |
| `data/`, `results/<extent>/mc/` | Raw inputs and raw replicate files (not in git) |
