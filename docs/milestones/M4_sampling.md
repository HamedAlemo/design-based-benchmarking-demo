# M4 Sampling arms

Goal: one sampler per arm that returns a valid `ElementSample` or `ClusterSample` with correct inclusion probabilities, plus the registry that wires samplers to estimators.

## Samplers (specs in PROTOCOL.md section 5, budgets in config/arms.yaml)

1. `allocation.py`:
   - `allocate(n, N_h, m_min, weights)`: give every stratum m_min = min(base, floor(n / (2H))), then split the remainder in proportion to `weights`. Round with the largest-remainder method. Cap each n_h at N_h and redistribute any excess. The result must sum to n, with every n_h >= 2 where N_h >= 2.
   - Weights are N_h S_h for D, with S_h = sqrt(e (1 − e)) by agreement level, and N_h for D2 and F.
2. `element.py`:
   - `srs_cells(rng, N, n)` (arm C).
   - `stratified_cells(rng, strat_column, lookup, n_h)` (arms D, D2, F). Draw without replacement inside each stratum.
   - Precompute per-stratum index arrays once per extent (cached `.npy`) so a draw never scans the full table.
   - Gather ref and maps from the memmaps with sorted indices.
3. `cluster.py`:
   - `srs_tiles_per_state(rng, tiles_meta, T)` (A0): pi = T / M_s.
   - `equal_per_tag(rng, chips_meta, total, eligible_mask)` (A1 with complete chips, B2 with all chips): split the total equally over the 5 tags. Redistribute shortfalls from tags with too few chips equally across the remaining tags, repeating until settled. pi = n_tag / M_tag, where M_tag counts eligible chips only.
   - Return the PSU ids. The `ClusterSample` slices `tiles_conf` / `chips_conf` and `*_disc` (for chips, at the requested tau index).
4. `arms.py` registry: for each arm, give its sampler, estimator kind, budgets, purity thresholds and `draws_from`.
   - A0w evaluates the A0 draw with the cluster design estimator.
   - B1 evaluates the A1 draw at each tau in [0, 0.75, 0.9, 1.0].
   - E evaluates the D draw with equal weights.
   - F draws K independent samples, one per model, and each is used only for that model's estimates.
   - Also provide `actual_cvpr_test_split()`: a fixed `ClusterSample` of the matched CVPR test tiles, with pi = 20 / M_s for documentation only (the real split was drawn from the CVPR frame, not ours; note this in the report).

## Validation

1. Fixed sizes: every element draw has exactly n cells and the planned n_h per stratum. Every cluster draw has the planned PSUs per stratum.
2. Weight identities: for element designs, the sum of w = N exactly (to float tolerance). For cluster designs, the sum of w over PSUs in stratum h = M_h exactly. For B2, the mean over 2,000 draws of sum(w x n_cells) is within 3 MCSE of N.
3. Uniform selection within strata. Cluster: 20,000 draws on the dev frame; for every PSU, observed frequency vs pi with |z| < 4 for all PSUs. Element: per stratum, bin the stratum's cells into 50 equal bins by index; the chi-square test over 20,000 draws must not reject at 0.001.
4. Pairing: A0w uses identical psu_index to A0 in the same replicate; same for B1 vs A1 and E vs D.
5. Determinism: the same seed gives identical samples; different replicate seeds give different samples.
6. Allocation tests: sums, caps, minimums, and the edge case where a stratum has fewer cells than m_min.
7. Eligibility: A1 never selects an incomplete chip; B2 can.
8. Speed: one draw plus gather in under 50 ms for element arms at n = 2000 on the full extent (with cached stratum indices). Cluster draws in under 10 ms.

## Acceptance checks

All validation items pass on dev; the speed check passes on full. Report the allocation tables (n_h per stratum for D, D2 and F at each n) and the A0 / A1 / B2 inclusion probabilities per stratum in reports/M4.md. Update STATUS.md and commit.
