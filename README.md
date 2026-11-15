# bow-design-pilot

Benchmarks of the World, methods pilot: design-based vs conventional benchmarking of land cover maps, tested against a known wall-to-wall truth (Chesapeake Bay Program 2021/22 1 m land cover, Maryland and Delaware).

This repository is built to be developed by Claude Code, mostly unattended. Humans set it up, approve two gates if needed, and read the reports.

## What is in here

| Path | What it is |
| --- | --- |
| `CLAUDE.md` | Standing rules for Claude Code. Read automatically at session start. |
| `docs/PROTOCOL.md` | The experimental protocol: population, models, nine sampling arms, estimators, Monte Carlo, figures. |
| `docs/HYPOTHESES.md` | Pre-registered criteria for H0 to H5. Do not edit after M5 starts. |
| `docs/DECISIONS.md` | Decision log. Every deviation from the protocol is recorded here. |
| `docs/milestones/` | One spec per milestone (M0 to M7), each with acceptance checks. |
| `docs/PROMPTS.md` | The exact prompts to paste into Claude Code (or send via Dispatch). |
| `config/` | All tunable choices: extent, classes and crosswalks, products, frames, arms, Monte Carlo. |
| `src/bowpilot/contracts.py` | Data contracts every module must honor (samples, designs, estimates). |
| `reports/` | Milestone reports written by Claude Code. Read these. |

## Pre-flight checklist (do this on the target laptop before dispatching)

1. Hardware: at least 32 GB RAM (64 GB preferred), 250 GB free disk, 8+ cores. The full extent is about 4 x 10^8 cells at 10 m.
2. Install Miniforge or Miniconda, Git, and Claude Code. Sign in to Claude Code.
3. Unzip this repo, `cd bow-design-pilot`, then `git init && git add -A && git commit -m "scaffold"`.
4. Google Earth Engine (needed only for Dynamic World):
   - Have a Cloud project registered for Earth Engine.
   - Run `earthengine authenticate` on the laptop. If you are remote, use `earthengine authenticate --auth_mode=notebook` (or `--auth_mode=remote` on older clients): it prints a URL you open on any device and a code you paste back.
   - Put the project id in `config/products.yaml` (`dynamic_world.gee_project`) or export `GEE_PROJECT=<id>`.
   - If this is not done, M1 downloads everything else, writes a blocking note in `reports/M1.md`, and stops before M2.
5. Optional: R is installed by the conda environment (`r-base`, `r-survey`) for the M3 cross-check. Nothing to do.

## How to run

Open Claude Code in the repo root and paste the master prompt from `docs/PROMPTS.md` ("Run everything"). It executes M0 to M6 in order, first on the small `dev` extent end to end, then on the `full` extent. It commits after each milestone and writes `reports/Mx.md`.

To run a single milestone, use its prompt in `docs/PROMPTS.md`.

## Where to look when you come back

- `reports/STATUS.md`: one-line status per milestone, updated after each step.
- `reports/M*.md`: what was done, acceptance checks with numbers, anything that blocked.
- `reports/RESULTS.md` (after M6): each hypothesis, its pre-registered criterion, the evidence and the verdict.
- `results/figures/`: the six paper figures.

## Human gates (Claude Code stops and waits only for these)

1. Earth Engine authentication missing or failing.
2. Reference class names that do not match the expected list in `config/classes.yaml` (the crosswalk would be a guess).
3. An acceptance check still failing after two documented fix attempts.
4. Free disk below 20 GB.
