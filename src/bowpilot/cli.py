"""Command line interface: one command per milestone step. Every command accepts --extent dev|full."""

from __future__ import annotations

import typer

from bowpilot.config import load_config
from bowpilot.logging_utils import setup_logging

app = typer.Typer(add_completion=False, help="bowpilot: design-based vs conventional benchmarking pilot.")

ExtentOpt = typer.Option(None, "--extent", "-e", help="dev | full (default: config/extent.yaml active)")


@app.command()
def data(extent: str = ExtentOpt, steps: str = typer.Option("all", help="comma list: boundaries,reference,"
                                                                       "products,ecoregions,cvpr,qa")) -> None:
    """M1: download inputs and put them on the 10 m analysis grid."""
    cfg = load_config(extent)
    setup_logging(f"M1_{cfg.extent}")
    from bowpilot.data.pipeline import run_data
    run_data(cfg, steps.split(","))


@app.command()
def population(extent: str = ExtentOpt) -> None:
    """M2: cell table, frames, strata, per-unit arrays and population truth."""
    cfg = load_config(extent)
    setup_logging(f"M2_{cfg.extent}")
    from bowpilot.population.pipeline import run_population
    run_population(cfg)


@app.command("validate-estimators")
def validate_estimators(extent: str = ExtentOpt, draws: int = typer.Option(5000)) -> None:
    """M3: real-data estimator checks on the dev cell table (synthetic checks run in pytest)."""
    cfg = load_config(extent)
    setup_logging(f"M3_{cfg.extent}")
    from bowpilot.validation.m3 import run_m3
    run_m3(cfg, draws)


@app.command("validate-sampling")
def validate_sampling(extent: str = ExtentOpt, speed_only: bool = typer.Option(False, "--speed-only")) -> None:
    """M4: sampler validation (sizes, weights, uniformity, pairing, determinism, speed)."""
    cfg = load_config(extent)
    setup_logging(f"M4_{cfg.extent}")
    from bowpilot.validation.m4 import run_m4
    run_m4(cfg, speed_only=speed_only)


@app.command()
def montecarlo(extent: str = ExtentOpt, resume: bool = typer.Option(False, "--resume"),
               arms: str = typer.Option("all"), jobs: int = typer.Option(-1)) -> None:
    """M5: Monte Carlo replicates for all arms and budgets, then summaries."""
    cfg = load_config(extent)
    setup_logging(f"M5_{cfg.extent}")
    from bowpilot.simulate.montecarlo import run_montecarlo
    run_montecarlo(cfg, resume=resume, arms=None if arms == "all" else arms.split(","), n_jobs=jobs)


@app.command()
def report(extent: str = ExtentOpt) -> None:
    """M6: figures, tables and the RESULTS.md draft."""
    cfg = load_config(extent)
    setup_logging(f"M6_{cfg.extent}")
    from bowpilot.report.run import run_report
    run_report(cfg)


@app.command()
def status() -> None:
    """Print reports/STATUS.md."""
    cfg = load_config()
    typer.echo((cfg.reports_dir / "STATUS.md").read_text())


if __name__ == "__main__":
    app()
