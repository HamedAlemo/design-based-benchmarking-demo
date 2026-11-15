# Decision log

Every choice that shapes the results, with its reason. Claude Code appends entries for any deviation or data-driven choice. Format: date, decision, reason, expected effect.

## Locked by the PI on 2026-11-15

| # | Decision | Reason |
| --- | --- | --- |
| 1 | Study area: Maryland and Delaware | Two states of very different area reproduce a real benchmark flaw (equal tiles per state). |
| 2 | Reference 2021/22 land cover; products for 2021 | Closest temporal match. |
| 3 | Models: WorldCover 2021, Dynamic World 2021, Esri/IO 2021. NLCD dropped for now | Three 10 m products; avoids the developed-open-space crosswalk problem. |
| 4 | Dynamic World annual summary = mode of the `label` band over 2021 | Standard, simple, reproducible. |
| 5 | A1 purity thresholds 0.75, 0.9 and 1.0 (plus 0.0 for the B1 decomposition) | Shows the dose-response of purity filtering. |
| 6 | A0 tiles = the original CVPR 2019 tile geometry (USGS quarter quadrangles); the real CVPR test split is evaluated as a fixed realization | Critique a real benchmark, not a straw man. |
| 7 | Budgets: n = 500, 1000, 2000 cells; T = 5, 10, 20 tiles per state; 50, 100, 200 chips | Spans small to typical benchmark sizes. |
| 8 | All nine arms included; all six hypotheses tested in phase 1 | Full factorial for the paper. |

## Set in the protocol on 2026-11-15 (changeable only with a logged reason)

| # | Decision | Reason |
| --- | --- | --- |
| 9 | Analysis grid EPSG:5070, 10 m (protocol draft said Sentinel-2 UTM) | Equal-area cells, so class proportions are area proportions; expected to match the reference CRS so 10 x 10 pixel blocks nest exactly; western Maryland lies outside UTM zone 18. |
| 10 | Population boundary = Census 2021 cartographic state boundaries (clipped to shoreline) | Excludes open bay and ocean water, which would inflate accuracy with easy water cells. |
| 11 | Cells need all 100 reference pixels valid | No imputation of the truth. |
| 12 | Product nodata, cloud and snow = class 0, counted wrong | Dropping them would hide a real failure mode. |
| 13 | Plurality ties broken by lower class code; tie count reported | Deterministic. |
| 14 | Development runs on a ~35 km x 33 km dev extent across the MD-DE border before the full run | Catch errors cheaply. |

## Entries added during development

(Claude Code appends below.)

| # | Date | Decision | Reason | Expected effect |
| --- | --- | --- | --- | --- |
| 15 | 2026-11-15 | Reference rasters are the 2024-edition county LULC GeoTIFFs (`*_lulc_2021_2024-Edition.tif`); harmonized classes are derived from the release's own static crosswalk `lulc_visualization_crosswalk-2024-edition.csv` (column `lc`, the 11-class land cover parent). Mapping written to `config/classes.yaml` `lulc_to_harmonized`. | The 2024 edition has no stand-alone LC raster (User Guide, "Data Organization and Structure"). M1 step 2. | None beyond the protocol's intent: the LC parent is the release's own land cover attribution. |
| 16 | 2026-11-15 | LC parent "Shrubland" mapped to harmonized 3 (low vegetation). Approved by the PI in chat. | 2024-edition name for the 2022-edition "Scrub/Shrub" class (protocol section 2 merges it into low vegetation). Not a case or punctuation normalization, so it went to the human gate. | None. |
| 17 | 2026-11-15 | LULC 75 "Tidal Wetlands Harvested Forest" (LC parent listed as "Low Vegetation; Barren") mapped to 3. Approved by the PI in chat. | Two parents listed. The riverine and terrene harvested-forest wetland codes (55, 65) have parent Low Vegetation only. M1 reports its pixel count. | Negligible if the class is rare (count reported in M1). |
| 18 | 2026-11-15 | LC parent names matched to `name_to_harmonized` case-insensitively ("Tree Canopy Over ..." vs "Tree Canopy over ..."). | Allowed normalization (`allow_name_normalization: true`). | None. |
| 19 | 2026-11-15 | Reference files downloaded from the ScienceBase public publish bucket `https://prod-is-usgs-sb-prod-publish.s3.amazonaws.com/<item id>/<file name>` (the S3 key listed in each ScienceBase file record). | The `sciencebase.usgs.gov/manager/...` URLs in the item JSON return an HTML application, not the file. Same bytes, same release. | None. |
| 20 | 2026-11-15 | Rao-Wu bootstrap weights include the finite population correction: w (1 - lambda + lambda n_h / (n_h - 1) mult), lambda = sqrt(1 - n_h / N_h). Protocol section 6 gives w n_h / (n_h - 1) mult. | The protocol form omits the fpc, so it overstates the SE when sampling fractions are large (A0 and A0w on dev; 40 of 150 PSUs in the M3 synthetic case: about +17%). With lambda the bootstrap variance of a linear statistic equals the linearized stratified variance, fpc included. Identical to the protocol form as n_h / N_h goes to 0 (all element arms). | Bootstrap SEs for F1, IoU, macroF1 and mIoU in cluster arms are smaller than with the protocol form, and correct rather than conservative. No effect on element arms beyond rounding. |
| 21 | 2026-11-15 | Analysis grid origin snapped outward to multiples of 640 m (the chip origin multiple), which are also multiples of 10 m. | Makes chip id (row // 64, col // 64) equal to the 640 m-aligned chip grid in frames.yaml. | None. The grid only gains empty margin cells outside the population. |
| 22 | 2026-11-15 | M3 synthetic bias check amended (approved by the PI after attempt 1): pass if \|bias - b2\| <= 3 MCSE, with b2 = (R V(X_hat) - Cov(Y_hat, X_hat)) / X^2 the analytic second-order ratio bias under the test design, and \|bias\| <= 0.002. OA coverage asserted at the larger test size only; the smaller size is reported. | Attempt 1 (logs/M3_synthetic_attempt1.out, logs/M3_synthetic_diagnosis.out): 13 cluster UA_c cells failed the raw 3 MCSE rule (bias about -0.001 at 40 PSUs) and all matched b2 within 2.2 MCSE; one element cell (n = 500) at -3.4 MCSE was chance (independent seeds: -0.70 and +0.86). Cluster OA coverage at 40 PSUs: 0.916 to 0.924 (SE ratio 0.975); at 80 PSUs: 0.936 to 0.940. The Hajek ratio estimator is consistent, not unbiased; the original rule tests for zero bias, which theory does not promise. | Estimators unchanged. Expect slight Wald under-coverage and O(1/m) UA bias for cluster arms with few PSUs (A0w at small T, especially on dev). These effects are below the H1 tolerances (0.002 OA, 0.005 UA/PA) at the test sizes but may matter for H2 at T = 5. |
| 23 | 2026-11-15 | M3 synthetic bias threshold: Bonferroni limit z = Phi^-1(1 - 0.01 / (2 F)) MCSE, F = number of bias cells tested across both designs and sizes (about 190, z about 3.9). Approved by the PI. Every cell beyond 3 MCSE is still listed in reports/M3.md. | With about 190 cells at 3 MCSE, about 0.5 false alarms are expected for correct estimators. Attempt 1 had one such cell (element n = 500, model 2, UA_2, -3.37 MCSE; independent seeds -0.70 and +0.86). Seeds were not changed. | None on estimates. The test now controls the familywise false alarm rate at 1%. |
| 24 | 2026-11-15 | M4 check 3 (cluster uniformity): per-PSU limit is the Bonferroni value Phi^-1(1 - 0.01 / (2 m)) over the m PSUs tested in the arm (about 4.5 for 2,700 PSUs), plus a per-stratum check that the SD of z lies in the two-sided chi-square 0.001 band. Approved by the PI. | Attempt 1 (dev): A1 max \|z\| = 4.26 over 2,695 chips against the fixed limit 4. Within tags, z had mean 0 and SD 0.88 to 1.05; the count of \|z\| > 3 matched chance in three further runs (logs/M4_dev_A1_diagnosis.out). A fixed limit of 4 fails a perfect sampler with probability 0.17 at 2,700 PSUs and almost surely at 100,000. | None on samples. The check keeps a 1% familywise false alarm rate at any frame size. |
| 25 | 2026-11-15 | M3 real-data A0w coverage check (dev, T = 5) recorded as a finding, not fixed. Approved by the PI. CIs stay Wald as the protocol says. | A0w OA coverage was 0.901 to 0.908 (SE ratio 0.93 to 0.95; bias within 3 MCSE) with 10 PSUs. The estimator matches R survey to 1e-13. A t-interval would likely help, but choosing it after seeing dev results would tune the method to dev. | A0w may under-cover at small T on the full extent too. If so, H2 condition 1 fails for A0w, and that is reported as is. |
