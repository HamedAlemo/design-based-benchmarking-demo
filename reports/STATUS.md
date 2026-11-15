# Status

BLOCKER (human gate 1): Earth Engine credentials are missing, so Dynamic World cannot be downloaded. M2 and later steps on real data wait on it. Run `conda activate bowpilot && earthengine authenticate`, then provide the Cloud project id. See reports/M1.md.

One line per milestone and extent. Claude Code updates this after every step.

| Milestone | dev | full | Notes |
| --- | --- | --- | --- |
| M0 Setup | done | n/a | |
| M1 Data and grid | done except Dynamic World | running (reference + products), DW blocked | All dev checks pass for WC and IO |
| M2 Cell table, frames, truth | code done, tested on synthetic extent; waits on DW | waits on DW | |
| M3 Estimators and validation | synthetic, R and speed checks pass; real-data check waits on M2 | n/a | Criteria amended with PI approval (DECISIONS.md entries 22, 23) |
| M4 Sampling arms | code done, tested on synthetic extent; waits on M2 | waits | |
| M5 Monte Carlo | code done, tested on synthetic extent | not started | HYPOTHESES.md frozen at start |
| M6 Figures and results | code done, tested on synthetic extent | not started | |
| M7 Phase 2 foundation models | deferred | deferred | Optional, not in the first run |
