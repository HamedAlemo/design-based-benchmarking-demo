"""Estimators, samplers and the Monte Carlo driver must never import the population truth (CLAUDE.md invariant 2)."""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "bowpilot"
GUARDED = ["estimation", "sampling", "simulate"]
PATTERN = re.compile(r"(from\s+bowpilot\.population(\.truth)?\s+import\s+.*truth|import\s+bowpilot\.population\.truth"
                     r"|from\s+\.\.population\s+import\s+truth|from\s+\.\.population\.truth\s+import)")


def test_no_truth_imports_in_guarded_packages():
    offenders = []
    for pkg in GUARDED:
        for py in (SRC / pkg).rglob("*.py") if (SRC / pkg).exists() else []:
            if PATTERN.search(py.read_text()):
                offenders.append(str(py))
    assert not offenders, f"truth imported in: {offenders}"
