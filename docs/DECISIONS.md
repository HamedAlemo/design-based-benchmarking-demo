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
