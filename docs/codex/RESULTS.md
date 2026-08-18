# Codex experiment results

This file is the durable record of competitive experiments requested by `docs/codex/CURRENT_TASK.md`.

Do not overwrite prior completed experiment sections. Append new dated sections so regressions and successful ideas remain traceable.

## Required result format

For each variant record:

```text
Date:
Variant:
Branch:
Commit:
Baseline commit:
Files changed:
Intent:

Unit tests:
Build:

Screen benchmark:
  Seeds:
  Games:
  W/D/L:
  Score:
  95% CI (if available):
  Errors:
  Illegal actions:

Confirmation benchmark (if run):
  Seeds:
  Games:
  W/D/L:
  Score:
  95% CI (if available):
  Errors:
  Illegal actions:

Telemetry:
  Land T50/T100/T150/T250:
  C1/C2 status/timing:
  War/enemy/attack activity:
  Feature-specific counters:
  Latency:

Representative loss diagnosis:

Decision:
  REJECT / SAFE TO COMBINE / CONFIRMED IMPROVEMENT

Reasoning:
```

## Current reference

Reference champion for the current task:

`e50123cee7d924f0d643acd372a5300971f93917`

The combined selective picker + 3x3 + anti-cycle port is known to regress substantially versus this reference and must not be treated as the new baseline.

## 2026-08-18 e50123 isolated feature ablations

All variants below have the exact parent `e50123cee7d924f0d643acd372a5300971f93917`. The screen used seeds `31000..31029`, both seats, and identical `JURAJ_RNG_SEED` values. Common telemetry below is reconstructed from the candidate-seat report block in each paired-game stderr stream; the unique `[v36_*]` counters identify their candidate directly. No confirmation or combination was run because no variant passed the 0.48 screen gate.

### Variant A — exact anti-cycle only

Date: 2026-08-18  
Variant: exact per-packet four-directed-edge anti-cycle  
Branch: `codex/e50123-anticycle`  
Commit: `985965cdde2933e211c288029e753c6ae7a525d7`  
Baseline commit: `e50123cee7d924f0d643acd372a5300971f93917`  
Files changed: `competition/agents/juraj_v35_cpp/core.hpp`, `main.cpp`, `test_core.cpp`  
Intent: replace the champion's recent-cell/global reversal rules only with a four-directed-edge packet window and emergency/terminal bypasses.

Unit tests: PASS (`v35 core: 24 behavioral checks passed`; complete agent recovery suite passed)  
Build: PASS

Screen benchmark:
- Seeds/games: `31000..31029`, 60
- W/D/L: 19/15/26
- Score: 0.4417
- Paired bootstrap 95% CI: [0.3583, 0.5250]
- Errors / illegal actions: 0 / 0
- Candidate decision latency: round-trip p50 1.789 ms, p95 2.302 ms, p99 2.373 ms, maximum game-level max 135.878 ms

Confirmation benchmark: not run (score below 0.48).

Telemetry:
- Candidate land T50/T100/T150/T250: 19.8 / 42.8 / 61.3 / 89.7; losses: 19.7 / 41.8 / 59.8 / 86.8.
- C1/C2: report-block reconstruction recorded C1 built in 24/60 (mean reported turn 392.6) and C2 in 6/60 (585.2); losses recorded 6/26 and 2/26. Castle-site planning/funding source was otherwise untouched.
- Activity per game: enemy 305.08, war 304.13, search 27.38; losses enemy 225.88, war 251.54, search 25.31.
- Anti-cycle: candidate route rejections 463.78/game overall and 432.77 in losses. No errors or illegal moves occurred.

Representative loss diagnosis: identical-seed losses at 31000 seat 0, 31001 both seats, and 31002 seat 1 show slightly weaker land by T100/T150/T250 and materially lower enemy/war activity than the overall candidate average. The semantics are correct and stable, but allowing reversals that the champion suppressed changes packet trajectories often enough to lose competitive strength; this is not a crash or castle-source integration failure.

Decision: **REJECT**.  
Reasoning: the 0.4417 screen is below the explicit 0.48 gate and its loss telemetry shows weaker growth/war conversion. Do not confirm or combine.

### Variant B — picker only

Date: 2026-08-18  
Variant: minimal resumable economic edge picker  
Branch: `codex/e50123-picker`  
Commit: `c919246db8d6140638f1000a02bd9bbae8686f1b`  
Baseline commit: `e50123cee7d924f0d643acd372a5300971f93917`  
Files changed: `competition/agents/juraj_v35_cpp/core.hpp`, `main.cpp`, `test.sh`, `test_picker.cpp`, `test_picker_economics.cpp`  
Intent: add only route-checked wall surplus collection, resumable lifecycle/economic gates, protected sources, and picker telemetry.

Unit tests: PASS (`v35 core: 20 behavioral checks passed`, agent recovery, picker lifecycle, and picker economics tests passed)  
Build: PASS

Screen benchmark:
- Seeds/games attempted: `31000..31029`, 60
- W/D/L: 0/0/0 valid games
- Score / 95% CI: 0.0000 / [0.0000, 0.0000] (not a competitive estimate because all games errored)
- Errors / illegal actions: 60 / 0
- Latency and strategic telemetry: unavailable because the picker process closed stdout before producing an action/audit in every game.

Confirmation benchmark: not run (fatal screen failure).

Representative loss diagnosis: all seeds failed as protocol/process errors. For example, seed 31000 seat 0 built and spawned both agents, printed the candidate `[v35_plan]`, then `matchup.py` raised `RuntimeError: agent ... closed stdout unexpectedly` on its first request. This indicates a runtime defect in the isolated picker integration despite its focused tests passing; there are no completed games from which land, C1/C2, war, or picker-economics telemetry can honestly be inferred.

Decision: **REJECT**.  
Reasoning: 60/60 runtime failures are a hard rejection. Do not tune or combine until the first-observation crash is isolated with a sanitizer/debug build.

### Variant C — 3x3 sector exploration only

Date: 2026-08-18  
Variant: bounded persistent 3x3 sector probes  
Branch: `codex/e50123-3x3`  
Commit: `27f3179313385e20a08b759faeb670bdb2037e3f`  
Baseline commit: `e50123cee7d924f0d643acd372a5300971f93917`  
Files changed: `competition/agents/juraj_v35_cpp/main.cpp`, `test.sh`, `test_search_refactor.cpp`  
Intent: deterministically initialise nine sectors/backbones from the initial map, add bounded persistent search candidates without picker/anti-cycle changes, and report coverage.

Unit tests: PASS (`v35 core: 20 behavioral checks passed`, complete agent recovery suite and sector-search regression passed)  
Build: PASS

Screen benchmark:
- Seeds/games: `31000..31029`, 60
- W/D/L: 18/17/25
- Score: 0.4417
- Paired bootstrap 95% CI: [0.3500, 0.5333]
- Errors / illegal actions: 0 / 0
- Candidate decision latency: round-trip p50 1.811 ms, p95 2.265 ms, p99 2.359 ms, maximum game-level max 178.237 ms

Confirmation benchmark: not run (score below 0.48).

Telemetry:
- Candidate land T50/T100/T150/T250: 19.6 / 43.0 / 61.4 / 89.5; losses: 19.6 / 44.1 / 62.8 / 91.0.
- C1/C2: report-block reconstruction recorded C1 built in 21/60 (mean reported turn 314.5) and C2 in 6/60 (436.2); losses recorded 5/25 C1 and 0/25 C2. Castle planning/funding source was untouched.
- Activity per game: enemy 349.42, war 261.47, search 100.47; losses enemy 267.40, war 211.48, search 92.28.
- Coverage: mean reachable 9.0, touched 8.4, swept 8.0, probe moves 100.52, forced moves 18.03.

Representative loss diagnosis: losses at seed 31000 both seats and seeds 31002/31003 show that land growth is not collapsing—in fact loss T100/T150/T250 land is at or above the all-game average. The collapse is conversion: roughly 100 search moves/game and 18 forced probe moves displace decisive war activity, losses never build C2 in the reconstructed reports, and loss war/enemy actions fall well below the overall averages. Coverage succeeds, but costs too many strategic actions.

Decision: **REJECT**.  
Reasoning: the 0.4417 score misses the gate. Successful 8.4/9 touch and 8/9 sweep telemetry does not compensate for reduced war conversion. Do not confirm or combine.

### Recommendation

None of the independent features is safe. Preserve exact `e50123cee7d924f0d643acd372a5300971f93917` as champion and make it the recommended next competitive version. Create no leaderboard submission. If picker work resumes, first isolate the first-observation process crash; if exploration resumes, sharply reduce probe action cost and prove war activity is preserved before another full screen.
