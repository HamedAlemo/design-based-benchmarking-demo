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


def test_no_truth_imports_ast():
    """AST check: catches `import`, `from ... import truth` and importlib strings naming the truth module."""
    import ast

    offenders = []
    for pkg in GUARDED:
        for py in (SRC / pkg).rglob("*.py"):
            tree = ast.parse(py.read_text())
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    mod = ("." * node.level) + (node.module or "")
                    names = [f"{mod}.{a.name}" for a in node.names] + [mod]
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if node.value.strip() in ("bowpilot.population.truth", "..population.truth"):
                        names = [node.value]
                if any(n.endswith("population.truth") or n.startswith("bowpilot.population.truth")
                       or n == "..population.truth" for n in names):
                    offenders.append(f"{py}:{node.lineno}")
    assert not offenders, f"truth imported in: {offenders}"
