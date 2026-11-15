# Protocol: design-based vs conventional benchmarking, Chesapeake pilot

Version 1.0, 2026-11-15. Decisions locked on this date are listed in `docs/DECISIONS.md`. The protocol is also kept as a doc in the Benchmarks of the World project.

## 1. Purpose

We show, against a known wall-to-wall truth, how far conventional benchmark protocols drift from true map accuracy and model ranking, and that a shared probability sample with known inclusion probabilities recovers both. Every benchmark score estimates some population quantity. A conventional score estimates it for an implicit, fictional population. A design-based score estimates it for a declared, real one. Here the truth is fully known, so the gap is measured, not argued.

Hypotheses H0 to H5 and their pre-registered decision criteria are in `docs/HYPOTHESES.md`.

## 2. Population, reference and assessment unit

Population U: every 10 m cell of the analysis grid whose center lies inside Maryland or Delaware (Census 2021 cartographic boundaries, clipped to the shoreline) and whose 100 underlying 1 m reference pixels are all valid. N = |U|.

Grid: EPSG:5070 (CONUS Albers equal area), 10 m cells, edges on multiples of 10 m. Equal-area cells make class proportions equal area proportions. M1 verifies that the reference is in EPSG:5070 and aligned to integer meters, so each cell aggregates exactly 10 x 10 reference pixels. If not, the reference is warped by nearest neighbor to an aligned 1 m grid first, and the change is logged.

Reference: Chesapeake Bay Land Use/Land Cover Database 2024 Edition (USGS data release, DOI 10.5066/P14BEBRC), land cover layer for 2021/22, organized by state and county. Its 5-class static land cover accuracy is 95% overall; class UA ranges from 63% (barren) to 98% (water). The reference is treated as truth by construction. Its own error affects all arms equally and does not change the comparison between arms.

Harmonized classes (codes used everywhere):

| Code | Class | Reference classes merged |
| --- | --- | --- |
| 1 | Water | Water |
| 2 | Tree canopy | Tree canopy; tree canopy over structures, other impervious and roads |
| 3 | Low vegetation | Low vegetation, scrub/shrub, emergent wetlands |
| 4 | Barren | Barren |
| 5 | Impervious | Impervious structures, other impervious, impervious roads |

Per cell we store: reference class r(u) = plurality of the 100 harmonized 1 m labels (ties broken by the lower class code, logged as a count); purity = plurality fraction (0.2 to 1.0); the five class fractions; state; tile id; chip id; stratum ids for D, D2 and F.

## 3. Models (phase 1)

Three existing 2021 products, each a different model's wall-to-wall map:

| Key | Product | Access |
| --- | --- | --- |
| worldcover_2021 | ESA WorldCover 2021 v200 | Planetary Computer `esa-worldcover` (v2.0.0) |
| dynamic_world_2021 | Dynamic World V1, annual mode of the `label` band over 2021 | Earth Engine |
| esri_io_2021 | Esri / Impact Observatory 10m Annual LULC v02, 2021 | Planetary Computer `io-lulc-annual-v02` |

Rules: nearest-neighbor resampling of each product to the analysis grid. Crosswalks in `config/classes.yaml`. Nodata, cloud, snow and unobserved pixels become class 0 (no prediction) and count as wrong. NLCD is excluded in this phase. Foundation-model probe maps are phase 2 (M7, optional).

## 4. Population truth

For model k, the true error matrix over all N cells:

$$p^{(k)}_{ij} = \frac{1}{N}\sum_{u \in U} \mathbb{1}[m_k(u)=i,\ r(u)=j], \quad i \in \{0,\dots,5\},\ j \in \{1,\dots,5\}$$

Derived truths: OA = sum over j of p_jj. UA_c = p_cc / p_c+. PA_c = p_cc / p_+c. F1_c = 2 p_cc / (p_c+ + p_+c). IoU_c = p_cc / (p_c+ + p_+c − p_cc). macroF1 and mIoU = means over c = 1..5. Reference area area_c = p_+c. Map-implied area = p_c+. Also: true rankings of models on OA, macroF1 and each F1_c; all quantities by state; restricted truths for the B1 target populations (complete chips, purity at least tau).

## 5. Sampling arms

Every arm returns, per sampled unit, its inclusion probability, stratum and PSU (`src/bowpilot/contracts.py`).

| Arm | Group | Selection | Estimator | Budgets per draw |
| --- | --- | --- | --- | --- |
| A0 | Conventional | CVPR-style tiles: T quarter-quadrangle tiles per state by SRS, all cells scored | Naive pooled: unweighted, binomial SE, McNemar on pooled pixels | T = 5, 10, 20 per state |
| A0w | Repair | Same draw as A0 | Design cluster: weights M_s / T, stratified one-stage cluster variance | as A0 |
| A1 | Conventional | 640 m chips; eligible = complete chips; equal number per rare-class tag; score only cells with purity at least tau | Naive pooled; also chip-averaged mIoU | 50, 100, 200 chips; tau = 0.75, 0.9, 1.0 |
| B1 | Repair | Same draw as A1 | Design cluster with correct chip weights M_tag / n_tag; purity filter kept | as A1; tau = 0, 0.75, 0.9, 1.0 |
| B2 | Repair | All chips with at least one population cell; equal number per tag | Design cluster; no purity filter | 50, 100, 200 chips |
| C | Design | SRS of cells | Design element (equal weights) | n = 500, 1000, 2000 |
| D | Design | Stratified by product agreement | Design element, Stehman (2014) | n = 500, 1000, 2000 |
| D2 | Design | Stratified by state x EPA Level III ecoregion | Design element | n = 500, 1000, 2000 |
| E | Mistake | Same draw as D | Naive unweighted: equal weights, binomial SE, McNemar | as D |
| F | Per-model reference | For each model separately, stratified by that model's own classes | Design element | n per model; total K x n |

Tile frame (A0, A0w). The CVPR 2019 tiles are USGS quarter quadrangles (3.75 arc-minute cells). The frame is the full quarter-quadrangle grid over the population; the actual CVPR MD and DE tiles must match grid cells (M2 checks this). A population cell belongs to the tile containing its center. A tile's stratum is the state holding most of its population cells. M_s = number of frame tiles in state s. Inclusion probability: pi = T / M_s for each tile in s. Because M_DE is much smaller than M_MD, Delaware cells are over-represented by the pooled estimator. The real CVPR test split (20 MD and 20 DE test tiles) is also evaluated once as a fixed realization.

Chip frame (A1, B1, B2). Chips are 64 x 64 cells on a 640 m grid. Rare-class tag of a chip: the rarest class, by population proportion, covering at least 5% of the chip's population cells. A1 and B1 select among complete chips only (all 4,096 cells in the population). B2 selects among all chips. Selection within each tag stratum is SRS; the requested total is split equally across the five tags; if a tag has fewer chips than its share, all of its chips are taken and the remainder is split across the other tags. pi = n_tag / M_tag.

Decomposition chain: A1 to B1(tau) removes the balancing effect; B1(tau) to B1(0) removes the purity filter; B1(0) to B2 removes the complete-chip restriction. A0 to A0w separates ignoring pi from the sample itself.

Strata for D. Consensus class = the class with at least two of three product votes, if that class is not 0. Agreement level = 3 of 3 or 2 of 3. All other cells form one "no majority" stratum. H is at most 11 strata. Allocation: at least m_min = min(50, floor(n / 2H)) per stratum; the remainder in proportion to N_h S_h with S_h = sqrt(e_h (1 − e_h)) and working error rates e = 0.05 (3 of 3), 0.40 (2 of 3), 0.60 (no majority). n_h is capped at N_h. pi = n_h / N_h. Strata use the phase 1 products being evaluated; this is valid because strata are fixed before sampling.

Strata for D2. State x EPA Level III ecoregion; strata below 0.5% of N merge into a per-state "other" stratum. Allocation: m_min = min(30, floor(n / 2H)), remainder proportional to N_h.

Strata for F. Model k's own map classes 0..5 (empty classes dropped). Allocation: m_min = min(50, floor(n / 2H)), remainder proportional. One independent sample per model.

## 6. Estimators and variance

Design weights w_u = 1 / pi_u (cluster designs: the PSU's weight applies to each of its scored cells).

$$\hat{p}^{(k)}_{ij} = \frac{\sum_{u \in s} w_u\, \mathbb{1}[m_k(u)=i,\ r(u)=j]}{\sum_{u \in s} w_u}$$

UA, PA, OA, area and paired differences are ratios R = Y / X of weighted totals (Hajek form, valid when strata are not the map classes; Stehman 2014). Linearized residual for each sampled cell:

$$z_u = \frac{y_u - \hat{R}\, x_u}{\hat{X}}$$

Stratified element designs (C, D, D2, F; and E only as a check):

$$\hat{V}(\hat{R}) = \sum_h N_h^2 \left(1 - \frac{n_h}{N_h}\right) \frac{s^2_{z,h}}{n_h}$$

Stratified one-stage cluster designs (A0w, B1, B2), with t_hi the sum of z over the scored cells of PSU i:

$$\hat{V}(\hat{R}) = \sum_h M_h^2 \left(1 - \frac{m_h}{M_h}\right) \frac{s^2_{t,h}}{m_h}$$

Because z is linear in y and x, t_hi is computed from the per-PSU confusion counts without cell-level data.

Naive estimators as practiced (A0, A1, E): unweighted pooled counts; binomial SE sqrt(p(1 − p) / n) where n is the relevant pixel count (all scored pixels for OA, pixels mapped c for UA_c, pixels of reference c for PA_c); no SE for F1, IoU, macroF1, mIoU. Pairwise test: McNemar z = (b − c) / sqrt(b + c) on pooled pixels, treated as independent.

Nonlinear parameters (F1_c, macroF1, IoU_c, mIoU, and their pairwise differences) in design arms: Rao-Wu rescaling bootstrap respecting strata and PSUs, on a subset of replicates (config). Within stratum h with n_h units, draw n_h − 1 units with replacement; bootstrap weight = w × n_h / (n_h − 1) × multiplicity.

Paired comparison of models k and l in design arms: d_u = 1[m_k(u) = r(u)] − 1[m_l(u) = r(u)], estimated as a ratio with x_u = 1 and the same design variance. A decision is significant when the 95% CI excludes 0.

Intervals: Wald 95%. Logit-scale intervals for rare-class UA and PA are a sensitivity analysis.

Model-assisted area (secondary, arm D): post-stratified estimator of area_c using model k's map as auxiliary data, area_c(PS, k) = sum over i of W_i^(k) p̂(r = c | m_k = i), with W_i^(k) the known map proportions. Report SE reduction relative to the sample-only estimator.

## 7. Monte Carlo

R replicates per arm and budget (1,000 full; 50 dev). Arms that reuse another arm's draw (A0w from A0, B1 from A1, E from D) are evaluated on the same draw. Seeds: SeedSequence(base_seed).spawn per (arm, budget), then per replicate.

Per arm, budget, model and parameter: bias, relative bias, Monte Carlo SE of the bias, RMSE, ratio of mean estimated SE to empirical SD, 95% CI coverage, mean CI width.

Per arm and budget: probability of selecting the truly best model (OA, macroF1); Kendall's tau between estimated and true ranking; pairwise decisions classified as correct-significant, not significant, wrong-significant (Type S), plus the sign-flip rate regardless of significance. With three models there are 3 pairs; across OA, macroF1 and five F1_c there are 21 pairwise decisions per replicate.

Application-facing secondary analyses: per-state domain estimates from D and D2 compared with A0; sample-based area_c vs map-implied area; model-assisted area SE reduction.

## 8. Figures and tables

1. Estimates vs truth: point and 95% CI per model from one typical draw per arm; true value as a vertical line. Panels OA, macroF1, UA_barren.
2. Ranking fidelity vs budget: probability of the correct best model and Type S rate, by arm.
3. CI coverage by arm against nominal 95%, with SE ratio.
4. Decomposition bridge: A0 to A0w; A1 to B1(tau) to B1(0) to B2.
5. Study area map: reference, D strata, one draw of sample locations per arm.
6. Efficiency (H5): per-model UA and PA CI width under D vs F against total labeling cost.

Table 1: true population metrics per model. Table 2: bias, RMSE and coverage by arm and budget for OA and macroF1. The real CVPR test split is marked on Figures 1 and 2.

## 9. References

- Stehman & Foody (2019), Key issues in rigorous accuracy assessment of land cover products, Remote Sensing of Environment.
- Stehman (2014), Estimating area and map accuracy for stratified random sampling when the strata are different from the map classes, International Journal of Remote Sensing.
- Olofsson et al. (2014), Good practices for estimating area and assessing accuracy of land change, Remote Sensing of Environment.
- Wadoux et al. (2021), Spatial cross-validation is not the right way to evaluate map accuracy, Ecological Modelling.
- de Bruin et al. (2022), Dealing with clustered samples for assessing map accuracy by cross-validation, Ecological Informatics.
- Robinson et al. (2019), Large scale high-resolution land cover mapping with multi-resolution data, CVPR.
- Rao & Wu (1988), Resampling inference with complex survey data, JASA.
