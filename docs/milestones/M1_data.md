# M1 Data and grid

Goal: every input on the 10 m analysis grid for the active extent. Outputs are GeoTIFFs in `data/<extent>/interim/rasters/`, all sharing one grid (same CRS, transform, shape).

Run on `dev` first, then `full`. The dev extent downloads only the reference counties that intersect its bbox.

## 1. Boundaries and grid

1. Download the Census cartographic boundary file (`config/extent.yaml`), keep MD (24) and DE (10), reproject to the grid CRS. For `dev`, intersect with the dev bbox.
2. Grid: bounds of the extent polygon in the grid CRS, snapped outward to multiples of 10 m. Save `data/<extent>/interim/grid.json` (crs, transform, width, height). All later rasters use exactly this grid.
3. Rasterize states by cell center (`all_touched=False`): `state.tif` (uint8; 1 = MD, 2 = DE, 0 = outside).

## 2. Reference (Chesapeake 2021/22 land cover)

1. Resolve DOI 10.5066/P14BEBRC to its ScienceBase item. Use `sciencebasepy` to list child items and files. The release is organized by state, then county. Find the land cover (LC) rasters for 2021/22 for every MD and DE county (for dev, only counties intersecting the bbox). Download with resume support. Write `data/<extent>/raw/reference/MANIFEST.csv` (county, file, url, bytes, sha256).
2. If the 2024 release has no separate LC raster, use the LULC raster and the data dictionary (also in the release) to map each LULC class to its land cover parent. Write the mapping into `config/classes.yaml` under `lulc_to_harmonized` and add a DECISIONS.md entry.
3. Inspect: CRS, resolution, pixel-grid origin, dtype, nodata, and class names (raster attribute table or data dictionary). Fill `observed_codes` and `nodata` in `config/classes.yaml`.
4. Human gate: if any observed class name cannot be matched to `name_to_harmonized` (after allowed normalization), stop and report the unmatched names.
5. Alignment: if the reference CRS equals the grid CRS and pixel edges sit on integer meters, aggregate directly. Otherwise read through a `WarpedVRT` (nearest neighbor) onto a 1 m grid aligned to the 10 m grid, and log the decision.
6. Aggregate to 10 m with windowed reads (for example 5,120 x 5,120 reference pixels = 512 x 512 cells per window, parallel with joblib). Steps per window:
   - Map codes to harmonized 1..5 with a lookup table; nodata becomes 0.
   - Reshape to (h/10, 10, w/10, 10) and count per class.
   - Write per-cell outputs: `ref_valid.tif` (0..100 valid pixels), `ref_frac_1.tif` to `ref_frac_5.tif` (counts 0..100, uint8), `ref_class.tif` (plurality class, ties to the lower code, 0 if ref_valid < 100), `ref_purity.tif` (plurality count 0..100).
   - Count plurality ties.
   - Where county rasters overlap, mosaic them with a VRT. Check that overlapping pixels agree, and report the disagreement count.

## 3. Products (2021)

All products are reprojected to the grid with nearest neighbor, crosswalked to 0..5 (`config/classes.yaml`), and written as `map_<key>.tif` (uint8).

1. WorldCover 2021 v200: Planetary Computer STAC `esa-worldcover`, filter `esa_worldcover:product_version = 2.0.0`, asset `map`, signed with `planetary_computer.sign`. Fallback: the public S3 bucket.
2. Esri / IO 2021: STAC `io-lulc-annual-v02`, datetime 2021, asset `data`. Items are UTM tiles, possibly in zones 17 and 18. Reproject each to the grid and merge, taking the first valid value.
3. Dynamic World 2021: Earth Engine.
   - Image: `ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1").filterDate("2021-01-01", "2022-01-01").filterBounds(region).select("label").reduce(ee.Reducer.mode()).unmask(255)`. Value 255 means no observation and becomes class 0.
   - Download with `ee.data.computePixels` in 1,024 x 1,024-cell blocks on the exact grid: `grid = {dimensions, affineTransform: {scaleX: 10, shearX: 0, translateX: x0, shearY: 0, scaleY: -10, translateY: y0}, crsCode: "EPSG:5070"}`.
   - Use 4 to 8 threads, retry with exponential backoff, and verify every block exists before mosaicking.
   - Fallback: `Export.image.toCloudStorage` or `toDrive` with the same crs and crsTransform.
   - If Earth Engine auth fails: finish everything else, write the blocker at the top of reports/M1.md, update STATUS.md, and stop (human gate).

## 4. Other layers

1. EPA Level III ecoregions: locate the current download on the EPA ecoregions page, record the URL in DECISIONS.md, clip, and rasterize by cell center to `eco_l3.tif` (uint16 code plus a lookup CSV).
2. CVPR spatial index: download `spatial_index.geojson` (`config/frames.yaml`), keep `md_1m_2013*` and `de_1m_2013*` tiles with their split attribute, and save `data/<extent>/interim/cvpr_tiles.gpkg` in the grid CRS.

## 5. QA (results go in reports/M1.md)

1. Reference proportions: harmonized class proportions per state (cells with ref_valid = 100, weighted by fractions). If the release has state or county land cover summary tables, compare to them after harmonizing; expect agreement within 0.5 points per class. If no tables exist, recount 1 m pixels directly in 5 random 2 x 2 km windows and require exact equality with the aggregated counts.
2. Quicklooks: 5 random 2 x 2 km windows. Each window has 5 panels: 1 m reference (harmonized), 10 m ref_class, and the three products. Save to `reports/figures/M1_qa_<i>.png`. Open each PNG, look at it, and describe in the report what you see (alignment, obvious crosswalk errors).
3. Alignment shift test: for each product, agreement with ref_class over a 1% random cell subset at offsets of −2..+2 cells in x and y. The maximum must be at offset (0, 0). Report the 5 x 5 agreement grid per product.
4. Distribution table: class proportions of reference and each product (including class 0) over population cells.
5. Coverage: share of in-state cells with ref_valid = 100, with ref_valid between 1 and 99, and with 0.

## Acceptance checks

| Check | Pass condition |
| --- | --- |
| Grid consistency | All rasters share CRS, transform and shape with grid.json |
| Reference classes | All observed names mapped; no human gate pending |
| Reference proportions | Within 0.5 points of published summaries, or exact match on the 5 windows |
| Alignment | Peak agreement at (0, 0) for all three products |
| Product coverage | Class 0 share below 1% for each product within the population (if above, report it and continue; it is a real model property) |
| Quicklooks | 5 PNGs saved and described |
| Overlap agreement | County overlap disagreement below 0.01% of overlapping pixels |

Write `reports/M1.md` (include data volumes and runtime), update STATUS.md, commit.
