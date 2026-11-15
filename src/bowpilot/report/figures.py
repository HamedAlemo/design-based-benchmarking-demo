"""The six paper figures (M6). PNG at 300 dpi and PDF to results/figures/, PNG copies to reports/figures/.

Arm colours by group: conventional reds (A0, A1), repair ambers (A0w, B1, B2), design blues (C, D, D2), the
mistake grey (E), per-model reference purple (F). Markers differ by arm. The real CVPR test split is a star.
"""

from __future__ import annotations

import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import rasterio  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from bowpilot.config import Config  # noqa: E402
from bowpilot.data.qa import class_cmap  # noqa: E402

STYLE = {"A0": ("#b2182b", "s"), "A1": ("#ef8a62", "v"), "A0w": ("#b35806", "D"), "B1": ("#e08214", "^"),
         "B2": ("#fdb863", "P"), "C": ("#2166ac", "o"), "D": ("#4393c3", "X"), "D2": ("#92c5de", "h"),
         "E": ("#878787", "*"), "F": ("#762a83", "p")}
ARMS = ["A0", "A0w", "A1", "B1", "B2", "C", "D", "D2", "E", "F"]
plt.rcParams.update({"font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8, "legend.fontsize": 7,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})


def _save(cfg: Config, fig, name: str) -> None:
    out = cfg.root / "results" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{name}_{cfg.extent}"
    fig.savefig(out / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(out / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)
    (cfg.reports_dir / "figures").mkdir(parents=True, exist_ok=True)
    shutil.copy(out / f"{stem}.png", cfg.reports_dir / "figures" / f"{stem}.png")


def fixed_budgets(cfg: Config) -> dict[str, tuple[int, float]]:
    """Figure 1 / 4 budgets: n = 1000, T = 10 (dev: middle value), 100 chips, tau = 0.9."""
    t = cfg.budgets("A0")
    tb = 10 if 10 in t else t[len(t) // 2]
    out = {a: (1000, 0.0) for a in ["C", "D", "D2", "E", "F"]}
    out |= {"A0": (tb, 0.0), "A0w": (tb, 0.0), "A1": (100, 0.9), "B1": (100, 0.9), "B2": (100, 0.0)}
    return out


def _short(cfg: Config) -> dict[str, str]:
    return cfg.model_short


def fig1_estimates(cfg: Config, mc: pd.DataFrame, truth: pd.DataFrame, cvpr: pd.DataFrame | None) -> None:
    keys = cfg.model_keys
    fb = fixed_budgets(cfg)
    params = [("OA", "OA"), ("macroF1", "macroF1"), ("UA_4", "UA barren")]
    tv = truth[truth.scope == "all"].set_index(["model", "parameter"])["value"]
    fig, axes = plt.subplots(len(params), len(keys), figsize=(7.2, 6.2), sharey=True)
    est = mc[mc.kind == "estimate"]
    for j, k in enumerate(keys):
        for i, (p, lab) in enumerate(params):
            ax = axes[i, j]
            for y, arm in enumerate(ARMS):
                b, tau = fb[arm]
                g = est[(est.arm == arm) & (est.budget == b) & (est.tau == tau) & (est.model == k)]
                if g.empty:
                    continue
                oa = g[g.parameter == "OA"].set_index("replicate")["estimate"]
                rep = (oa - oa.mean()).abs().idxmin()          # typical replicate: OA closest to the arm mean
                row = g[(g.replicate == rep) & (g.parameter == p)].iloc[0]
                c, m = STYLE[arm]
                if np.isfinite(row.se):
                    ax.plot([row.ci_low, row.ci_high], [y, y], color=c, lw=1.4)
                ax.plot(row.estimate, y, marker=m, color=c, ms=5, ls="none")
            if cvpr is not None and not cvpr.empty:
                for arm, yy in [("A0", ARMS.index("A0") - 0.35), ("A0w", ARMS.index("A0w") - 0.35)]:
                    r = cvpr[(cvpr.arm == arm) & (cvpr.model == k) & (cvpr.parameter == p) & (cvpr.kind == "estimate")]
                    if len(r):
                        r = r.iloc[0]
                        if np.isfinite(r.se):
                            ax.plot([r.ci_low, r.ci_high], [yy, yy], color="k", lw=0.8)
                        ax.plot(r.estimate, yy, marker="*", color="k", ms=7, ls="none")
            ax.axvline(tv[(k, p)], color="k", lw=0.9, ls="--")
            ax.set_yticks(range(len(ARMS)))
            ax.set_yticklabels([f"{a}" for a in ARMS])
            ax.invert_yaxis()
            if i == 0:
                ax.set_title(_short(cfg)[k])
            if j == 0:
                ax.set_ylabel(lab)
            ax.tick_params(axis="x", labelsize=7)
    fig.suptitle("Figure 1. One typical replicate per arm: estimate and 95% CI. Dashed line: population truth. "
                 "Star: real CVPR test split.", fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _save(cfg, fig, "fig1_estimates_vs_truth")


def _cells_per_draw(mc: pd.DataFrame) -> pd.DataFrame:
    e = mc[(mc.kind == "estimate") & (mc.parameter == "OA")]
    return e.groupby(["arm", "budget", "tau"])["n_cells_scored"].mean().rename("cells").reset_index()


def fig2_ranking(cfg: Config, rank: pd.DataFrame, cells: pd.DataFrame) -> None:
    r = rank[rank.metric == "OA"].merge(cells, on=["arm", "budget", "tau"], how="left")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for arm in ARMS:
        taus = [0.9] if arm in ("A1", "B1") else [0.0]
        g = r[(r.arm == arm) & r.tau.isin(taus)].sort_values("cells")
        if g.empty:
            continue
        c, m = STYLE[arm]
        cells_x = g["cells"] * (3 if arm == "F" else 1)        # F labels K x n cells
        axes[0].plot(cells_x, g["p_best_correct"], marker=m, color=c, label=arm, lw=1)
        axes[1].plot(cells_x, g["type_s"], marker=m, color=c, lw=1)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xlabel("labelled cells per draw (log)")
    axes[0].set_ylabel("P(true best model on OA)")
    axes[1].set_ylabel("Type S rate, OA pairs")
    axes[1].axhline(0.025, ls="--", color="k", lw=0.8)
    axes[0].legend(ncol=2, frameon=False, loc="lower right")
    fig.suptitle("Figure 2. Ranking fidelity vs labelling cost (A1/B1 at tau = 0.9)", fontsize=8)
    fig.tight_layout()
    _save(cfg, fig, "fig2_ranking_vs_budget")


def fig3_coverage(cfg: Config, est: pd.DataFrame) -> None:
    s = est[(est.scope == "all") & (est.parameter == "OA") & est.coverage.notna()]
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True)
    labels, pos = [], []
    x = 0.0
    for arm in ARMS:
        for (b, tau), gg in s[s.arm == arm].groupby(["budget", "tau"]):
            c, m = STYLE[arm]
            axes[0].plot([x] * len(gg), gg["coverage"], marker=m, color=c, ls="none", ms=4)
            axes[1].plot([x] * len(gg), gg["se_ratio"], marker=m, color=c, ls="none", ms=4)
            labels.append(f"{arm} {b}" + (f" t{tau:g}" if arm in ("A1", "B1") else ""))
            pos.append(x)
            x += 1
        x += 0.5
    axes[0].axhspan(0.93, 0.97, color="#cccccc", alpha=0.5, lw=0)
    axes[0].axhline(0.95, color="k", lw=0.6)
    axes[0].set_ylabel("OA 95% CI coverage")
    axes[1].axhline(1.0, color="k", lw=0.6)
    axes[1].set_ylabel("mean SE / empirical SD")
    axes[1].set_xticks(pos)
    axes[1].set_xticklabels(labels, rotation=90, fontsize=6)
    fig.suptitle("Figure 3. OA coverage (band 0.93 to 0.97) and SE ratio by arm and budget; one marker per model",
                 fontsize=8)
    fig.tight_layout()
    _save(cfg, fig, "fig3_coverage")


def fig4_bridge(cfg: Config, est: pd.DataFrame) -> None:
    fb = fixed_budgets(cfg)
    s = est[(est.parameter == "OA") & (est.scope == "all")]
    a1 = s[(s.arm == "A1") & (s.budget == fb["A1"][0]) & (s.tau == 0.9)]
    model = a1.loc[a1["bias"].abs().idxmax(), "model"]
    steps = [("A1(0.9)", "A1", fb["A1"][0], 0.9), ("B1(0.9)", "B1", fb["B1"][0], 0.9),
             ("B1(0)", "B1", fb["B1"][0], 0.0), ("B2", "B2", fb["B2"][0], 0.0),
             ("A0", "A0", fb["A0"][0], 0.0), ("A0w", "A0w", fb["A0w"][0], 0.0)]
    fig, ax = plt.subplots(figsize=(5.5, 3.0))
    prev = None
    for i, (_lab, arm, b, tau) in enumerate(steps):
        r = s[(s.arm == arm) & (s.budget == b) & (s.tau == tau) & (s.model == model)]
        if r.empty:
            continue
        r = r.iloc[0]
        c, _ = STYLE[arm]
        base = prev if (prev is not None and i not in (0, 4)) else 0.0
        ax.bar(i, r["bias"] - base, bottom=base, color=c, width=0.6)
        ax.errorbar(i, r["bias"], yerr=2 * r["mcse_bias"], color="k", capsize=3, lw=0.8)
        prev = r["bias"]
    ax.axhline(0, color="k", lw=0.6)
    ax.axvline(3.5, color="grey", lw=0.6, ls=":")
    ax.set_xticks(range(len(steps)))
    ax.set_xticklabels([s_[0] for s_ in steps])
    ax.set_ylabel(f"OA bias, {cfg.model_short[model]}")
    ax.set_title("Figure 4. Decomposition: balancing, purity filter, complete-chip restriction; ignoring pi (±2 MCSE)",
                 fontsize=8)
    fig.tight_layout()
    _save(cfg, fig, "fig4_decomposition")


def fig5_study_area(cfg: Config) -> None:
    from bowpilot.grid import Grid
    from bowpilot.sampling.arms import Context

    grid = Grid.from_json(cfg.interim_dir / "grid.json")
    f = max(1, int(np.ceil(max(grid.width, grid.height) / 1500)))
    with rasterio.open(cfg.rasters_dir / "ref_class.tif") as s:
        ref = s.read(1, out_shape=(grid.height // f, grid.width // f), resampling=rasterio.enums.Resampling.mode)
    ctx = Context(cfg)
    row, col = np.load(cfg.cells_dir / "row.npy", mmap_mode="r"), np.load(cfg.cells_dir / "col.npy", mmap_mode="r")
    sd = np.load(cfg.cells_dir / "strat_D.npy", mmap_mode="r")
    sub = np.arange(0, len(row), max(1, len(row) // 3_000_000))
    dmap = np.full(ref.shape, np.nan)
    rr, cc = np.asarray(row[sub]) // f, np.asarray(col[sub]) // f
    ok = (rr < dmap.shape[0]) & (cc < dmap.shape[1])
    dmap[rr[ok], cc[ok]] = np.asarray(sd[sub])[ok]
    rng = np.random.Generator(np.random.PCG64(cfg.base_seed + 5))
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 5.0))
    cmap, norm = class_cmap()
    axes[0, 0].imshow(ref, cmap=cmap, norm=norm, interpolation="nearest")
    axes[0, 0].set_title("Reference (10 m plurality)")
    axes[0, 1].imshow(dmap, cmap=ListedColormap(plt.cm.tab20.colors[:11]), vmin=-0.5, vmax=10.5,
                      interpolation="nearest")
    axes[0, 1].set_title("D strata (consensus x agreement)")
    for ax, arm, b in [(axes[0, 2], "C", 1000), (axes[1, 0], "D", 1000)]:
        s = ctx.draw(arm, b, rng).element
        ax.imshow(ref > 0, cmap=ListedColormap(["white", "#eeeeee"]), interpolation="nearest")
        ax.plot(np.asarray(col[s.cell_index]) / f, np.asarray(row[s.cell_index]) / f, ".", ms=1.2,
                color=STYLE[arm][0])
        ax.set_title(f"{arm}: one draw, n = {b}")
    t = fixed_budgets(cfg)["A0"][0]
    d = ctx.draw("A0", t, rng)
    ax = axes[1, 1]
    ax.imshow(ref > 0, cmap=ListedColormap(["white", "#eeeeee"]), interpolation="nearest")
    tile = np.load(cfg.cells_dir / "tile.npy", mmap_mode="r")
    sel = np.isin(np.asarray(tile[sub]), d.cluster_psu[0])
    ax.plot(np.asarray(col[sub])[sel] / f, np.asarray(row[sub])[sel] / f, ",", color=STYLE["A0"][0])
    ax.set_title(f"A0: one draw, {t} tiles per state")
    d = ctx.draw("A1", 100, rng)
    ax = axes[1, 2]
    ax.imshow(ref > 0, cmap=ListedColormap(["white", "#eeeeee"]), interpolation="nearest")
    cm = pd.read_parquet(cfg.interim_dir / "frames" / "chips_frame.parquet").set_index("chip_id")
    size = cfg.chip_size
    for cid in d.cluster_psu[0]:
        r0, c0 = cm.loc[cid, "chip_row"] * size / f, cm.loc[cid, "chip_col"] * size / f
        ax.add_patch(Rectangle((c0, r0), size / f, size / f, color=STYLE["A1"][0]))
    ax.set_title("A1: one draw, 100 complete chips")
    for ax in axes.ravel():
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle(f"Figure 5. Study area ({cfg.extent} extent) and one draw per design", fontsize=8)
    fig.tight_layout()
    _save(cfg, fig, "fig5_study_area")


def fig6_efficiency(cfg: Config, eff: pd.DataFrame) -> None:
    keys = cfg.model_keys
    fig, axes = plt.subplots(1, len(keys), figsize=(7.2, 2.6), sharey=True)
    for ax, k in zip(np.atleast_1d(axes), keys, strict=True):
        g = eff[eff.model == k]
        for prefix, ls in [("UA", "-"), ("PA", "--")]:
            gg = g[g.parameter.str.startswith(prefix)].groupby("budget")[["mean_ci_width_D", "mean_ci_width_F"]].mean()
            ax.plot(gg.index, gg["mean_ci_width_D"], ls=ls, marker=STYLE["D"][1], color=STYLE["D"][0],
                    label=f"D {prefix}")
            ax.plot(gg.index * 3, gg["mean_ci_width_F"], ls=ls, marker=STYLE["F"][1], color=STYLE["F"][0],
                    label=f"F {prefix}")
        ax.set_xscale("log")
        ax.set_title(cfg.model_short[k])
        ax.set_xlabel("total labels (D: n, F: 3n)")
    np.atleast_1d(axes)[0].set_ylabel("mean 95% CI width (avg over classes)")
    np.atleast_1d(axes)[0].legend(frameon=False, fontsize=6)
    fig.suptitle("Figure 6. Shared stratified sample (D) vs per-model samples (F): UA and PA CI width vs cost",
                 fontsize=8)
    fig.tight_layout()
    _save(cfg, fig, "fig6_efficiency")
