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

## 2026-08-19 — selective picker v3 clean transplant and full screen

Date: 2026-08-19
Variant: selective picker v3 clean transplant (A/B combined gate)
Branch: `codex/e50123-picker-selective-v3-clean`
Frozen source commit: `fb29962110ea4f3d451aefb426daf0321b0ff4b4`
Baseline commit: `e50123cee7d924f0d643acd372a5300971f93917`
Files changed: `competition/agents/juraj_v35_cpp/{core.hpp,main.cpp,paired_benchmark.py,test.sh,test_picker.cpp,test_picker_economics.cpp,test_protocol.py}` plus this task/results documentation.
Intent: transplant only the existing selective picker, its telemetry, focused tests, and protocol regression onto the exact champion. No threshold or policy change was made before or after the screen.

Ancestry proof:
`git merge-base fb29962110ea4f3d451aefb426daf0321b0ff4b4 e50123cee7d924f0d643acd372a5300971f93917`
returned exactly `e50123cee7d924f0d643acd372a5300971f93917`.

Gate preserved from the prototype: an economically viable ray must first exceed
16 surplus and 2.0 projected units per move. A start then requires turn >=150
or >=35% map ownership; our land >=80% of opponent land; growth >=2 cells/25
turns or >=3 cells/50 turns (waived at >=45% map ownership); at most three
immediately capturable neutral frontiers; top-three owned-stack share <55%; and
no existing owned stack as large as the proposed delivery. The front/general
sink is observed but is not a hard gate.

Unit/recovery/picker/protocol tests: PASS
Release build: PASS

Protocol smoke:
  Seeds: 31000..31009, both seats
  Games: 20
  W/D/L: 4/3/13
  Score: 0.2750
  Paired bootstrap 95% CI: [0.1250, 0.4250]
  Errors: 0
  Illegal actions: 0
  Mean per-game decision p50: 1.902 ms; p95 of per-game p50: 2.603 ms; maximum observed decision: 183.026 ms
  Picker: 1,351 eligible snapshots, 0 starts/completions/dedicated moves/piggyback moves/delivered mass
  Gate rejects: economy 0, behind 947, growth stalled 224, neutral opportunities 180, concentration 0, no-sink 0

Full development screen:
  Seeds: 31000..31029, both seats
  Games: 60
  W/D/L: 11/10/39
  Score: 0.2667
  Paired bootstrap 95% CI: [0.1833, 0.3583]
  Errors: 0
  Illegal actions: 0
  Mean per-game decision p50: 3.255 ms; p95 of per-game p50: 6.759 ms; maximum observed decision: 408.925 ms

Screen telemetry (candidate per-game means unless stated otherwise):
  Land T50/T100/T150/T250: 18.95 / 41.52 / 59.58 / 86.57 (T250 available in 58 games)
  Expansion actions: 130.92
  Offense/enemy actions: 282.23
  War actions: 327.88
  Search actions: 33.35
  C1: built in 20/60 games, mean turn 398.65
  C2: built in 6/60 games, mean turn 649.67
  Picker eligible snapshots: 4,064
  Picker starts/completions: 0 / 0
  Dedicated/piggyback picker moves: 0 / 0
  Delivered mass / mass per dedicated move: 0 / not applicable
  Picker start-turn distribution: empty
  Gate rejects: economy unhealthy 0; too far behind 2,621; growth stalled 574; too many expansion opportunities 869; concentration sufficient 0; no useful sink 0; other 0

The screen score is below the explicit 0.48 continuation threshold. Therefore
the 32000 development confirmation was not run, no holdout candidate was
frozen, and the untouched 33000 and 34000 pools were not examined.

Five-win / five-loss forensic check:
  Wins inspected: seeds/seat 31000/1, 31002/0, 31006/0, 31007/0, 31013/1.
  Losses inspected: 31000/0, 31001/0, 31001/1, 31002/1, 31003/0.
  Every inspected game had zero picker starts, zero delivered mass, and zero
  dedicated moves. Thus none of the five wins demonstrates a picker benefit,
  and none of the five losses can honestly be blamed on an activated picker.
  Meaningful contact occurred in all ten games, but the selective gate rejected
  every proposed start before a concentrated attack packet could be attributed
  to picker activity. This also exposes a serious integration concern: despite
  no starts, the clean candidate was far from behaviorally equivalent to the
  exact champion and regressed decisively.

Decision: **REJECT**

Reasoning: runtime was clean, but the full paired development screen was a
decisive regression (0.2667, upper CI 0.3583). The mandatory threshold stops
the sequence before 32000 and before any fresh holdout. No submission ZIP was
created.
