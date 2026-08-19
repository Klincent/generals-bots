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

## 2026-08-19 — selective economy-safe picker v3 (incomplete validation)

Date: 2026-08-19
Variant: A/B combined selective gate prototype
Branch: `codex/e50123-picker-selective-v3`
Baseline commit: `e50123cee7d924f0d643acd372a5300971f93917`
Implementation base: non-modal picker `b1edc4015f5e0a9f8c4f306e458e0d64d849d734`

The prototype records a snapshot for every mass/efficiency-eligible start and
requires expansion maturity (turn 150 or 35% map ownership), no worse than a
20% land deficit, recent growth (2 cells/25 turns or 3 cells/50 turns, waived
at 45% map ownership), at most three immediately capturable neutral frontiers,
top-three stack share below 55%, and no existing stack as large as the proposed
delivery. A known front or confirmed enemy general is recorded but is not a
hard requirement.

Unit tests: PASS (`bash competition/agents/juraj_v35_cpp/test.sh`)
Build: PASS (`bash competition/agents/juraj_v35_cpp/build.sh`)
Protocol smoke benchmark: 1 map / 2 games on seed 31000, 1 W / 0 D / 1 L,
score 0.5000, paired 95% bootstrap CI [0.5000, 0.5000], 0 errors, 0 illegal
actions. This is only a runner smoke test and is not evidence of improvement.

The required 60/120-game development runs and untouched holdouts were not
completed. Consequently no candidate was frozen, no 33000 or 34000 holdout was
examined, and no win/loss forensic claim is made.

Decision: **REJECT**

Reasoning: the task requires competitive evidence. A runtime prototype without
the prescribed full development and holdout results cannot be recommended or
submitted, irrespective of local correctness.
