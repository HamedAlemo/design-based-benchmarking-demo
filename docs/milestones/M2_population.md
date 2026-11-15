# M2 Cell table, frames, strata and truth

Goal: fix the population once, build the sampling frames and strata, precompute per-PSU sufficient statistics, and compute the exact population truth. After M2 nothing reads rasters again except QA and figures.

## 1. Population and cell table

1. Population mask: `state > 0` and `ref_valid == 100`. Report N per state and the number of in-state cells excluded for incomplete reference.
2. Cell order: row-major over the grid. Store `row.npy` and `col.npy` (int32) for population cells in `data/<extent>/interim/cells/`.
3. Columns, each a `.npy` memmap of length N:

| File | dtype | Content |
| --- | --- | --- |
| ref.npy | uint8 | reference class 1..5 |
| purity.npy | uint8 | plurality count 0..100 |
| frac_1.npy to frac_5.npy | uint8 | class counts 0..100 |
| map_worldcover_2021.npy, map_dynamic_world_2021.npy, map_esri_io_2021.npy | uint8 | model classes 0..5 |
| state.npy | uint8 | 1 MD, 2 DE |
| eco.npy | uint16 | EPA L3 code |
| tile.npy | int32 | tile id (section 2) |
| chip.npy | int32 | chip id (section 3) |
| strat_D.npy | uint8 | D stratum id |
| strat_D2.npy | uint16 | D2 stratum id |
| strat_F_<model>.npy | uint8 | F stratum id for that model (= its map class) |

Build the columns with windowed reads; never hold a full-extent raster in memory for the full run.

## 2. Tile frame (A0, A0w)

1. Build quarter-quadrangle polygons (0.0625 degree cells in EPSG:4269) covering the extent. Project them to the grid CRS.
2. Assign each population cell to the tile containing its center (rasterize tile ids by center). Every population cell must get exactly one tile.
3. Tile stratum = the state with the most population cells in the tile. Frame = tiles with at least one population cell. Report M_MD, M_DE, and the tile size distribution (cells per tile).
4. Match the CVPR tiles: for each MD and DE 2013 CVPR tile, take the frame tile containing its centroid and compute IoU in the grid CRS. Require IoU >= 0.8. Save `cvpr_match.csv` (cvpr name, split, tile id, IoU).
   - If more than 5% fail to match, try EPSG:4326 for the grid. If still failing, diagnose and document; this becomes a human gate after two attempts.
   - Record which frame tiles form the real CVPR test split.
   - CVPR used 2013 extents. Tiles are matched by geometry only; their 2021/22 labels come from our reference.

## 3. Chip frame and tags (A1, B1, B2)

1. Chip id from (row // 64, col // 64) on a 640 m-aligned grid. Store cells per chip. A chip is complete if all 4,096 of its cells are in the population.
2. Rarity order of classes = ascending population proportion of ref (computed here and saved).
3. Tag of a chip = the rarest class whose share of the chip's population cells is >= 5%.
4. Report: chips per tag, for complete chips and for all chips.

## 4. Strata

- D: votes from the three maps per cell. If some class != 0 has at least 2 votes, stratum = (that class, 3 of 3 or 2 of 3). Otherwise the cell goes to "no majority". Save the lookup (id, consensus class, level, N_h).
- D2: state x EPA L3 code. Strata under 0.5% of N merge into "<state>_other". Save the lookup with N_h.
- F: for each model, stratum = its map class 0..5, empty classes dropped. Save N_h per model.

## 5. Per-PSU arrays (`data/<extent>/interim/units/`)

P = number of model pairs (3), in fixed order (0,1), (0,2), (1,2).

| File | Shape | Content |
| --- | --- | --- |
| tiles_conf.npy | (M_tiles, K, 6, 5) int64 | counts of (map class, ref class) over all population cells in the tile |
| tiles_disc.npy | (M_tiles, P, 2) int64 | McNemar counts per pair |
| tiles_meta.parquet | M_tiles rows | tile id, stratum (state), n_cells, CVPR name and split if matched |
| chips_conf.npy | (M_chips, 4, K, 6, 5) int64 | as above, per purity threshold tau in [0, 0.75, 0.9, 1.0] (scored = purity >= 100 tau) |
| chips_disc.npy | (M_chips, 4, P, 2) int64 | McNemar counts per tau |
| chips_meta.parquet | M_chips rows | chip id, tag, complete flag, n_cells, n_scored per tau |

Compute them with chunked `np.bincount` on a combined index (unit, model, map class, ref class); do not loop over cells in Python.

## 6. Truth (`population/truth.py`, the only module allowed to compute metrics on the full table)

1. For each model: the 6 x 5 confusion counts over U, then every parameter from PROTOCOL.md section 4 (OA, UA_c, PA_c, F1_c, macroF1, IoU_c, mIoU, area_c, map-implied area). Use the same `estimation/params.py` metric functions the estimators use, applied to population counts.
2. Scopes:
   - `all`
   - `state=MD` and `state=DE`
   - `restricted_tau=<t>` for each tau: complete chips only, with purity >= tau. These are the B1 target populations.
3. True rankings of the models on OA, macroF1 and each F1_c, plus true pairwise differences.
4. Save `results/<extent>/truth/truth.parquet` (scope, model, parameter, value) and the confusion count arrays.
5. Independent cross-check: recompute the `all` confusion counts directly from the rasters with a separate windowed code path. The counts must be identical integers.

## Acceptance checks

| Check | Pass condition |
| --- | --- |
| Cell table | All columns length N; no ref = 0; no map value outside 0..5 |
| Tiles | Every population cell has one tile; the sum of tile n_cells equals N |
| Chips | Sum of chip n_cells equals N; complete-chip count reported |
| CVPR match | At least 95% of MD and DE CVPR tiles matched with IoU >= 0.8; test split identified |
| Strata | Sum of N_h equals N for D, D2 and each F |
| Unit arrays | Sum over tiles of tiles_conf equals the population confusion counts exactly; same for chips at tau = 0 |
| Truth cross-check | Raster path and table path counts identical |
| Table 1 draft | True metrics per model written to reports/M2.md |

Write `reports/M2.md`, including a short paragraph on how different the three models truly are (OA and macroF1 gaps), since this sets expectations for H3. Update STATUS.md and commit.
