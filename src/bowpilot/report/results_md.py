"""Draft of reports/RESULTS.md from the summaries and the frozen criteria (edited by hand afterwards).

For the dev extent the draft goes to reports/RESULTS_dev_draft.md and is labelled a smoke test, not evidence.
"""

from __future__ import annotations

import hashlib
import json
import subprocess

import pandas as pd

from bowpilot.config import Config
from bowpilot.report import hypotheses as H

CRITERIA = {
    "H1": "Conventional arms are biased for population accuracy; design arms are not.",
    "H2": "Naive SEs from clustered or unweighted samples under-cover; design SEs reach nominal coverage.",
    "H3": "Design arms rarely produce confidently wrong comparisons; conventional arms can, or pick the wrong best "
          "model more often.",
    "H4": "Purity filtering inflates accuracy, and weighting cannot repair it because excluded cells have zero "
          "inclusion probability.",
    "H5": "One model-agnostic stratified sample (D) gives per-model UA and PA precision close to per-model "
          "stratified samples (F) at one-Kth of the labeling cost.",
}


def _md(df: pd.DataFrame, cols: list[str] | None = None, digits: int = 4, max_rows: int = 60) -> str:
    d = df[cols] if cols else df
    d = d.head(max_rows).copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.{digits}f}")
    head = "| " + " | ".join(map(str, d.columns)) + " |\n| " + " | ".join("---" for _ in d.columns) + " |\n"
    return head + "".join("| " + " | ".join(map(str, r)) + " |\n" for r in d.itertuples(index=False))


def _parts(parts: dict) -> str:
    return "\n".join(f"- Condition {k}: {'met' if v else 'not met'}" for k, v in parts.items())


def evaluate(cfg: Config) -> dict:
    sd = cfg.results_dir / "summary"
    est = pd.read_parquet(sd / "estimates_summary.parquet")
    rank = pd.read_parquet(sd / "ranking_summary.parquet")
    eff = pd.read_parquet(sd / "efficiency_summary.parquet")
    truth = pd.read_parquet(cfg.results_dir / "truth" / "truth.parquet")
    return {"H1": H.h1(est), "H2": H.h2(est), "H3": H.h3(est, rank, truth), "H4": H.h4(est), "H5": H.h5(eff),
            "H0": H.h0(est, rank, truth), "est": est, "rank": rank, "truth": truth}


def draft(cfg: Config) -> str:
    ev = evaluate(cfg)
    truth = ev["truth"]
    t = truth[truth.scope == "all"]
    oa = t[t.parameter == "OA"].set_index("model")["value"]
    mf = t[t.parameter == "macroF1"].set_index("model")["value"]
    lines = []
    title = "Results" if cfg.extent == "full" else "Results draft (dev extent, smoke test, not evidence)"
    lines.append(f"# {title}\n")
    if cfg.extent != "full":
        lines.append("This draft is generated from the dev-extent smoke run "
                     f"({cfg.mc_profile['replicates']} replicates). Verdicts here are not evidence; they only test "
                     "the reporting pipeline. HYPOTHESES.md verdicts come from the full extent only.\n")
    lines.append("## 1. Summary for the PI\n")
    lines.append("(Written by hand after review.)\n")
    lines.append("True OA and macroF1 per model:\n")
    lines.append(_md(pd.DataFrame({"model": oa.index, "OA": oa.values, "macroF1": mf.reindex(oa.index).values})))
    lines.append("\n## 2. Hypotheses\n")
    lines.append("Interpretation used throughout: design-set conditions must hold for each design arm separately; "
                 "'every budget' means every budget configured for the extent.\n")
    for h in ["H1", "H2", "H3", "H4", "H5"]:
        verdict, parts, tabs = ev[h]
        lines.append(f"### {h}\n")
        lines.append(f"Claim: {CRITERIA[h]} Criterion: see docs/HYPOTHESES.md, section {h}.\n")
        lines.append(_parts(parts) + "\n")
        lines.append(f"Verdict: {verdict}.\n")
        for name, tab in tabs.items():
            if isinstance(tab, pd.DataFrame) and len(tab):
                lines.append(f"Table {h}.{name}:\n")
                lines.append(_md(tab) + "\n")
            elif tab is not None and not isinstance(tab, pd.DataFrame):
                lines.append(f"{name}: {json.dumps(tab, default=str)}\n")
    lines.append("### H0 (reported, no pass or fail)\n")
    lines.append(_md(ev["H0"]) + "\n")
    gaps = {f"{a}|{b}": round(float(oa[a] - oa[b]), 4) for i, a in enumerate(oa.index) for b in oa.index[i + 1:]}
    lines.append(f"True OA gaps between models: {json.dumps(gaps)}\n")
    lines.append("## 3. Surprises and limitations\n\n(Written by hand.)\n")
    lines.append("## 4. Reproducibility\n")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=cfg.root).stdout.strip()
    hyp = hashlib.sha256((cfg.root / "docs" / "HYPOTHESES.md").read_bytes()).hexdigest()
    rt = cfg.results_dir / "mc" / "runtimes.json"
    lines.append(f"- Commit: {commit}\n- HYPOTHESES.md SHA-256: {hyp}\n- Base seed: {cfg.base_seed}\n"
                 f"- Replicates: {cfg.mc_profile['replicates']}, bootstrap subset {cfg.mc_profile['bootstrap_subset']}"
                 f", B = {cfg.mc_profile['bootstrap_B']}\n"
                 f"- Monte Carlo wall time (s): {rt.read_text() if rt.exists() else 'n/a'}\n")
    return "\n".join(lines)


def write_draft(cfg: Config) -> str:
    text = draft(cfg)
    name = "RESULTS.md" if cfg.extent == "full" else f"RESULTS_{cfg.extent}_draft.md"
    path = cfg.reports_dir / name
    if cfg.extent == "full" and path.exists():
        path = cfg.reports_dir / "RESULTS_generated.md"      # never overwrite the hand-edited file
    path.write_text(text)
    return str(path)
