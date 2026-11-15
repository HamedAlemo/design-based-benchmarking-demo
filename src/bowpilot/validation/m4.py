"""M4 sampler validation: sizes, weight identities, uniform selection, pairing, determinism, eligibility, speed.

run_m4(cfg) runs every check on the extent's cell table and writes results/<extent>/validation/m4.json plus the
allocation and inclusion-probability tables for reports/M4.md.
"""

from __future__ import annotations

import json
import logging
import time

import numpy as np
import pandas as pd
from scipy.stats import chi2

from bowpilot.config import Config
from bowpilot.sampling.arms import Context

log = logging.getLogger(__name__)


def _rng(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(seed)))


def check_sizes_and_weights(ctx: Context, draws: int = 20) -> dict:
    cfg = ctx.cfg
    res = {}
    rng = _rng(1)
    for arm in ["C", "D", "D2", "F"]:
        ok_n = ok_h = ok_w = True
        for n in cfg.budgets(arm):
            for _ in range(draws):
                d = ctx.draw(arm, n, rng)
                samples = d.per_model if arm == "F" else [d.element]
                for j, s in enumerate(samples):
                    ok_n &= len(s.cell_index) == n and len(np.unique(s.cell_index)) == n
                    if arm != "C":
                        planned = ctx.allocation(arm, n, cfg.model_keys[j] if arm == "F" else None)
                        got = np.array([(s.stratum == i).sum() for i in [x.stratum_id for x in s.strata]])
                        ok_h &= bool(np.array_equal(planned, got))
                    ok_w &= bool(np.isclose((1 / s.pi).sum(), ctx.N, rtol=1e-12))
        res[arm] = {"exact_n": bool(ok_n), "planned_n_h": bool(ok_h), "sum_w_equals_N": bool(ok_w)}
    for arm in ["A0", "A1", "B2"]:
        ok_m = ok_w = True
        for b in cfg.budgets(arm):
            for _ in range(draws):
                d = ctx.draw(arm, b, rng)
                psu, pi, st, info = d.cluster_psu
                for si in info:
                    m = st == si.stratum_id
                    ok_m &= int(m.sum()) == si.sampled_units
                    if si.sampled_units:
                        ok_w &= bool(np.isclose((1 / pi[m]).sum(), si.population_units, rtol=1e-12))
                ok_m &= len(np.unique(psu)) == len(psu)
        res[arm] = {"planned_psus": bool(ok_m), "sum_w_equals_M_h": bool(ok_w)}
    return res


def check_b2_total(ctx: Context, draws: int = 2000) -> dict:
    rng = _rng(2)
    n_cells = ctx.chips_meta["n_cells"].to_numpy()
    b = ctx.cfg.budgets("B2")[0]
    tot = np.empty(draws)
    for i in range(draws):
        psu, pi, _, _ = ctx.draw("B2", b, rng).cluster_psu
        tot[i] = (n_cells[psu] / pi).sum()
    mcse = tot.std(ddof=1) / np.sqrt(draws)
    return {"budget": b, "mean": float(tot.mean()), "N": ctx.N, "mcse": float(mcse),
            "z": float((tot.mean() - ctx.N) / mcse) if mcse > 0 else 0.0,
            "pass": bool(abs(tot.mean() - ctx.N) <= 3 * mcse) if mcse > 0 else bool(np.isclose(tot.mean(), ctx.N))}


def check_cluster_uniform(ctx: Context, draws: int = 20000, family_alpha: float = 0.01) -> dict:
    """Per-PSU selection frequency vs pi (DECISIONS.md entry 24, approved by the PI).

    Pass if every PSU has |z| below the Bonferroni limit Phi^-1(1 - alpha / (2 m)) over the m PSUs tested in the arm,
    no eligible PSU is never selected, and in each stratum with at least 10 PSUs the SD of z is inside the two-sided
    chi-square 0.001 band. (The per-stratum mean of z is exactly 0 by construction, so it is not tested.)
    """
    from scipy.stats import norm

    out = {}
    rng = _rng(3)
    for arm in ["A0", "A1", "B2"]:
        b = ctx.cfg.budgets(arm)[0]
        m_units = len(ctx.tiles_meta) if arm == "A0" else len(ctx.chips_meta)
        cnt = np.zeros(m_units)
        pi_u = np.zeros(m_units)
        for _ in range(draws):
            psu, pi, _, _ = ctx.draw(arm, b, rng).cluster_psu
            cnt[psu] += 1
            pi_u[psu] = pi
        eligible = np.ones(m_units, bool) if arm != "A1" else ctx.chip_complete.astype(bool)
        strat = ctx.tiles_meta["stratum"].to_numpy() if arm == "A0" else ctx.chip_tag
        sel = eligible & (pi_u > 0) & (pi_u < 1)
        p = pi_u[sel]
        z = (cnt[sel] / draws - p) / np.sqrt(p * (1 - p) / draws)
        never = int((eligible & (cnt == 0)).sum())
        limit = float(norm.ppf(1 - family_alpha / (2 * max(len(z), 1))))
        sd_ok, sd_tab = True, {}
        for s in np.unique(strat[sel]):
            zz = z[strat[sel] == s]
            if len(zz) >= 10:
                lo, hi = np.sqrt(chi2.ppf([0.0005, 0.9995], len(zz) - 1) / (len(zz) - 1))
                sd = float(zz.std(ddof=1))
                sd_tab[str(int(s))] = {"n": len(zz), "sd_z": round(sd, 3), "band": [round(lo, 3), round(hi, 3)]}
                sd_ok &= bool(lo <= sd <= hi)
        out[arm] = {"budget": b, "max_abs_z": float(np.abs(z).max()) if len(z) else 0.0, "z_limit": limit,
                    "n_psus": int(sel.sum()), "n_abs_z_gt_4": int((np.abs(z) > 4).sum()),
                    "eligible_never_selected": never, "sd_by_stratum": sd_tab,
                    "pass": bool((np.abs(z) < limit).all()) and never == 0 and sd_ok}
        if arm == "A1":
            out["A1"]["incomplete_ever_selected"] = int(cnt[~ctx.chip_complete.astype(bool)].sum())
    return out


def check_element_uniform(ctx: Context, draws: int = 20000, bins: int = 50) -> dict:
    """Per stratum: bin cells into 50 equal bins by stratum position; chi-square over draws must not reject at 0.001.
    Run for D (all strata) and C (one stratum)."""
    out = {}
    rng = _rng(4)
    for arm in ["C", "D"]:
        n = ctx.cfg.budgets(arm)[0]
        if arm == "C":
            groups = {0: (0, ctx.N)}
            pos_of = lambda s: s.cell_index  # noqa: E731
        else:
            si = ctx.si["strat_D"]
            inv = None
            groups = {int(i): (int(st), int(nh)) for i, st, nh in zip(si.ids, si.start, si.N_h, strict=True)}
            inv = np.empty(len(si.order), dtype=np.int64)
            inv[np.asarray(si.order)] = np.arange(len(si.order))
            pos_of = lambda s, inv=inv: inv[s.cell_index]  # noqa: E731
        counts = {h: np.zeros(bins) for h in groups}
        for _ in range(draws):
            s = ctx.draw(arm, n, rng).element
            pos = pos_of(s)
            for h, (start, nh) in groups.items():
                p = pos[s.stratum == h] - start
                counts[h] += np.bincount((p * bins // nh).astype(np.int64), minlength=bins)[:bins]
        res = {}
        for h, (_start, nh) in groups.items():
            c = counts[h]
            edges = (np.arange(bins + 1) * nh + bins - 1) // bins          # exact cells per bin
            expected = c.sum() * np.diff(edges) / nh
            stat = float(((c - expected) ** 2 / expected).sum())
            p = float(chi2.sf(stat, bins - 1))
            res[str(h)] = {"chi2": round(stat, 2), "p": p}
        out[arm] = {"strata": res, "pass": all(v["p"] >= 0.001 for v in res.values())}
    return out


def _draw_key(d) -> np.ndarray:
    if d.cluster_psu is not None:
        return d.cluster_psu[0]
    return d.per_model[0].cell_index if d.per_model else d.element.cell_index


def check_pairing_and_determinism(ctx: Context) -> dict:
    cfg = ctx.cfg
    ok_pair = True
    for arm in ["A0", "A1", "D"]:
        d = ctx.draw(arm, cfg.budgets(arm)[0], _rng(5))
        labels = [lab for lab, _, _ in ctx.evaluate(d)]
        units = {lab: es.n_units for lab, _, es in ctx.evaluate(d)}
        partner = {"A0": "A0w", "A1": "B1", "D": "E"}[arm]
        ok_pair &= partner in labels and units[partner] == units[arm]
        if arm == "A0":
            ok_pair &= bool(np.array_equal(ctx.tile_sample(d).psu_index, ctx.tile_sample(d).psu_index))
    same, diff = True, True
    for arm in ["A0", "A1", "B2", "C", "D", "D2", "F"]:
        b = cfg.budgets(arm)[0]
        a1, a2, a3 = ctx.draw(arm, b, _rng(10)), ctx.draw(arm, b, _rng(10)), ctx.draw(arm, b, _rng(11))
        same &= bool(np.array_equal(_draw_key(a1), _draw_key(a2)))
        diff &= not np.array_equal(_draw_key(a1), _draw_key(a3))
    return {"pairing": bool(ok_pair), "same_seed_identical": bool(same), "different_seed_differs": bool(diff)}


def check_speed(ctx: Context, reps: int = 30) -> dict:
    out = {}
    rng = _rng(6)
    for arm, b in [("C", 2000), ("D", 2000), ("D2", 2000), ("A0", ctx.cfg.budgets("A0")[-1]),
                   ("A1", ctx.cfg.budgets("A1")[-1]), ("B2", ctx.cfg.budgets("B2")[-1])]:
        ctx.draw(arm, b, rng)
        t = []
        for _ in range(reps):
            t0 = time.perf_counter()
            d = ctx.draw(arm, b, rng)
            if d.cluster_psu is not None:
                ctx.tile_sample(d) if arm == "A0" else ctx.chip_sample(d, 0.0)
            t.append(time.perf_counter() - t0)
        ms = 1000 * float(np.median(t))
        out[arm] = {"budget": b, "median_ms": round(ms, 2), "pass": ms < (50 if arm in ("C", "D", "D2") else 10)}
    return out


def tables(ctx: Context) -> dict:
    cfg = ctx.cfg
    alloc = {}
    for arm in ["D", "D2"]:
        si = ctx.si[f"strat_{arm}"]
        alloc[arm] = pd.DataFrame({"stratum_id": si.ids, "N_h": si.N_h} |
                                  {f"n={n}": ctx.allocation(arm, n) for n in cfg.budgets(arm)})
    for k in cfg.model_keys:
        si = ctx.si[f"strat_F_{k}"]
        alloc[f"F_{k}"] = pd.DataFrame({"stratum_id": si.ids, "N_h": si.N_h} |
                                       {f"n={n}": ctx.allocation("F", n, k) for n in cfg.budgets("F")})
    pis = []
    for arm in ["A0", "A1", "B2"]:
        for b in cfg.budgets(arm):
            _, _, _, info = ctx.draw(arm, b, _rng(7)).cluster_psu
            for si in info:
                pis.append({"arm": arm, "budget": b, "stratum": si.stratum_id, "M_h": si.population_units,
                            "m_h": si.sampled_units, "pi": si.sampled_units / si.population_units})
    return {"allocation": {k: v.to_dict("records") for k, v in alloc.items()}, "cluster_pi": pis}


def run_m4(cfg: Config, uniform_draws: int = 20000, b2_draws: int = 2000, speed_only: bool = False) -> dict:
    """All M4 checks; with speed_only (full extent) the sizes/weights, pairing, speed checks and tables only."""
    ctx = Context(cfg)
    res = {}
    checks = [("sizes_weights", lambda: check_sizes_and_weights(ctx)),
                     ("b2_total", lambda: check_b2_total(ctx, b2_draws)),
                     ("cluster_uniform", lambda: check_cluster_uniform(ctx, uniform_draws)),
                     ("element_uniform", lambda: check_element_uniform(ctx, uniform_draws)),
                     ("pairing_determinism", lambda: check_pairing_and_determinism(ctx)),
                     ("speed", lambda: check_speed(ctx)),
                     ("tables", lambda: tables(ctx))]
    if speed_only:
        checks = [c for c in checks if c[0] in ("sizes_weights", "pairing_determinism", "speed", "tables")]
    for name, fn in checks:
        t0 = time.time()
        res[name] = fn()
        log.info("M4 %s done in %.1fs", name, time.time() - t0)
    out = cfg.results_dir / "validation"
    out.mkdir(parents=True, exist_ok=True)
    (out / ("m4_speed.json" if speed_only else "m4.json")).write_text(json.dumps(res, indent=2, default=str))
    return res
