"""SRS and stratified SRS of cells (arms C, D, D2, F). M4 item 2.

Per-stratum index arrays are precomputed once per extent and cached as .npy (order + offsets), so a draw never
scans the full table. Gathers ref and maps from the cell-table memmaps with sorted indices.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from bowpilot.contracts import ElementSample, StratumInfo


@dataclass
class StratumIndex:
    """Cells grouped by stratum: order (N,) int64 cell indices sorted by stratum; offsets per stratum id."""

    ids: np.ndarray        # (H,) stratum ids with N_h > 0
    N_h: np.ndarray        # (H,)
    start: np.ndarray      # (H,) offset into order
    order: np.ndarray      # (N,) int32 (memmap when cached)

    def strata(self, n_h: np.ndarray) -> list[StratumInfo]:
        return [StratumInfo(int(i), int(a), int(b)) for i, a, b in zip(self.ids, self.N_h, n_h, strict=True)]


def build_stratum_index(column: np.ndarray, cache_path=None) -> StratumIndex:
    """Index of a stratum column (any int dtype); cached to cache_path (.npz) if given."""
    order_path = cache_path.with_suffix(".order.npy") if cache_path is not None else None
    if cache_path is not None and cache_path.exists() and order_path.exists():
        z = np.load(cache_path)
        return StratumIndex(z["ids"], z["N_h"], z["start"], np.load(order_path, mmap_mode="r"))
    col = np.asarray(column)
    order = np.argsort(col, kind="stable").astype(np.int32 if len(col) < 2**31 else np.int64)
    counts = np.bincount(col.astype(np.int64))
    ids = np.nonzero(counts)[0]
    N_h = counts[ids]  # noqa: N806
    start = np.concatenate([[0], np.cumsum(N_h)[:-1]])
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(order_path, order)
        np.savez(cache_path, ids=ids, N_h=N_h, start=start)
    return StratumIndex(ids, N_h, start, order)


def gather(idx: np.ndarray, ref: np.ndarray, maps: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """ref (n,) and maps (n, K) for sorted cell indices."""
    return np.asarray(ref[idx]), np.stack([np.asarray(m[idx]) for m in maps], axis=1)


def srs_cells(rng: np.random.Generator, N: int, n: int, ref, maps) -> ElementSample:  # noqa: N803
    """Arm C: simple random sample of n cells without replacement; pi = n / N; one stratum (id 0)."""
    idx = np.sort(rng.choice(N, size=n, replace=False)).astype(np.int64)
    r, m = gather(idx, ref, maps)
    return ElementSample(idx, np.full(n, n / N), np.zeros(n, dtype=np.int32), [StratumInfo(0, N, n)], r, m)


def stratified_cells(rng: np.random.Generator, si: StratumIndex, n_h: np.ndarray, ref, maps) -> ElementSample:
    """Arms D, D2, F: SRS without replacement inside each stratum; pi = n_h / N_h."""
    parts, strat, pis = [], [], []
    for j in range(len(si.ids)):
        k = int(n_h[j])
        if k == 0:
            continue
        pos = rng.choice(int(si.N_h[j]), size=k, replace=False)
        parts.append(np.asarray(si.order[si.start[j] + pos]).astype(np.int64))
        strat.append(np.full(k, si.ids[j], dtype=np.int32))
        pis.append(np.full(k, k / si.N_h[j]))
    idx = np.concatenate(parts)
    o = np.argsort(idx)
    idx, st, pi = idx[o], np.concatenate(strat)[o], np.concatenate(pis)[o]
    r, m = gather(idx, ref, maps)
    return ElementSample(idx, pi, st, si.strata(n_h), r, m)
