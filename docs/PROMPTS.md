# Prompts for Claude Code

Paste these into Claude Code at the repo root, or send them through Dispatch. Each prompt is self-contained because the repo carries the context.

## 1. Run everything (master prompt)

```text
You are working in the bow-design-pilot repository. Read CLAUDE.md, docs/PROTOCOL.md, docs/HYPOTHESES.md and docs/DECISIONS.md first.

Execute the milestones in docs/milestones/ in order: M0, then M1 to M4 on the dev extent, M5 on dev (smoke profile), M6 on dev (draft figures only), then M1, M2, M4, M5 and M6 on the full extent. M3 runs once (synthetic tests plus the dev real-data check) and must fully pass before any Monte Carlo. Do not start M7.

For every milestone: implement it to its spec, run pytest and ruff, check every acceptance criterion, write reports/Mx.md with the numbers, update reports/STATUS.md, log any deviation in docs/DECISIONS.md, and commit.

Work autonomously. Stop and wait only for the human gates listed in CLAUDE.md. When a gate blocks one step, finish all independent work first, then write the blocker at the top of reports/STATUS.md and stop.

Long steps (downloads, aggregation, Monte Carlo) can take hours. Run them in the background with logging, poll their progress, and keep checkpoints so they can resume. Before each long step, note the expected runtime in STATUS.md.

At the end, reports/RESULTS.md must give a verdict for each hypothesis, traceable to the summary tables, after the adversarial review described in M6.
```

## 2. Single milestone

```text
Read CLAUDE.md and docs/milestones/<MX_file>.md. Implement milestone <MX> for extent <dev|full> exactly to spec. Run pytest and ruff, verify every acceptance check, write reports/<MX>.md, update reports/STATUS.md, log deviations in docs/DECISIONS.md, and commit. Stop only for the human gates in CLAUDE.md.
```

## 3. Resume after an interruption

```text
Read CLAUDE.md and reports/STATUS.md. Find the last completed step and any partial outputs (check logs/ and the resume markers in results/). Continue from there without redoing completed work. Follow the master prompt in docs/PROMPTS.md for the remaining milestones.
```

## 4. Unblock after Earth Engine authentication

```text
Earth Engine authentication is now set up (project id: <PROJECT_ID>). Put it in config/products.yaml, run the Dynamic World step of M1 for the extent(s) that were blocked, re-run the M1 acceptance checks, then continue with the master prompt from where STATUS.md says it stopped.
```

## 5. Status check (short, for a phone)

```text
Summarize reports/STATUS.md and the latest milestone report in 5 lines: what is done, what is running and its ETA, any blocker, and the most important number so far. Do not change anything.
```

## 6. Explain a result

```text
Read reports/RESULTS.md and results/<extent>/summary/. Explain the verdict for <H#> in plain language for a skeptical remote sensing audience, quoting the deciding numbers. Do not change any files.
```
