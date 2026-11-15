"""SRS of tiles per state (A0); equal-per-tag chip selection with redistribution (A1, B2). M4 item 3."""

from __future__ import annotations

import numpy as np

from bowpilot.contracts import ClusterSample, StratumInfo


def srs_tiles_per_state(rng: np.random.Generator, stratum: np.ndarray, T: int) -> tuple[np.ndarray, np.ndarray,  # noqa: N803
                                                                                          np.ndarray, list]:
    """Select min(T, M_s) tiles by SRS in each state stratum. pi = T / M_s.

    stratum : (M_tiles,) state code per frame tile. Returns (psu ids, pi, stratum per psu, StratumInfo list).
    """
    ids, pis, sts, info = [], [], [], []
    for s in np.unique(stratum):
        pool = np.nonzero(stratum == s)[0]
        k = min(T, len(pool))
        sel = np.sort(rng.choice(pool, size=k, replace=False))
        ids.append(sel)
        pis.append(np.full(k, k / len(pool)))
        sts.append(np.full(k, s, dtype=np.int32))
        info.append(StratumInfo(int(s), len(pool), k))
    return np.concatenate(ids), np.concatenate(pis), np.concatenate(sts), info


def tag_quotas(total: int, M_tag: dict[int, int], order: list[int]) -> dict[int, int]:  # noqa: N803
    """Equal split of `total` over tags; tags with fewer chips than their share give all their chips and the
    shortfall is split equally over the remaining tags, repeating until settled. Integer remainders go to tags in
    `order` (rarest first)."""
    tags = [t for t in order if M_tag.get(t, 0) > 0]
    if total > sum(M_tag[t] for t in tags):
        raise ValueError("total exceeds eligible chips")
    quota = {t: 0 for t in tags}
    open_ = list(tags)
    left = total
    while left > 0 and open_:
        base, rem = divmod(left, len(open_))
        share = {t: base + (1 if i < rem else 0) for i, t in enumerate(open_)}
        nxt = []
        for t in open_:
            take = min(share[t], M_tag[t] - quota[t])
            quota[t] += take
            left -= take
            if quota[t] < M_tag[t]:
                nxt.append(t)
        open_ = nxt
    return quota


def equal_per_tag(rng: np.random.Generator, tag: np.ndarray, eligible: np.ndarray, total: int,
                  order: list[int]) -> tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    """Select chips: SRS within each tag stratum among eligible chips, quotas from tag_quotas. pi = n_tag / M_tag."""
    M_tag = {int(t): int(((tag == t) & eligible).sum()) for t in order}  # noqa: N806
    quota = tag_quotas(total, M_tag, order)
    ids, pis, sts, info = [], [], [], []
    for t in order:
        if M_tag[t] == 0:
            continue
        pool = np.nonzero((tag == t) & eligible)[0]
        k = quota[t]
        info.append(StratumInfo(int(t), M_tag[t], k))
        if k == 0:
            continue
        ids.append(np.sort(rng.choice(pool, size=k, replace=False)))
        pis.append(np.full(k, k / M_tag[t]))
        sts.append(np.full(k, t, dtype=np.int32))
    return np.concatenate(ids), np.concatenate(pis), np.concatenate(sts), info


def cluster_sample(psu: np.ndarray, pi: np.ndarray, st: np.ndarray, info: list, conf: np.ndarray,
                   disc: np.ndarray, tau: float = 0.0) -> ClusterSample:
    """Build a ClusterSample by slicing the unit arrays (already indexed at the right tau for chips)."""
    o = np.argsort(psu)
    psu, pi, st = psu[o], pi[o], st[o]
    return ClusterSample(psu.astype(np.int64), pi, st, info, np.asarray(conf[psu]), np.asarray(disc[psu]), tau)
