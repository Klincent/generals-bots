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

## 2026-08-19 — selective picker v3 zero-picker equivalence repair

Date: 2026-08-19
Variant: selective picker v3 integration-equivalence repair
Branch: `codex/e50123-picker-selective-v3-equivalence`
Baseline commit: `e50123cee7d924f0d643acd372a5300971f93917`
Candidate parent: `fb29962110ea4f3d451aefb426daf0321b0ff4b4`
Files changed: `competition/agents/juraj_v35_cpp/main.cpp` (runtime disable
switch and restoration of champion logistics),
`competition/agents/juraj_v35_cpp/equivalence_check.py` (robust action-only
checker), and `competition/matchup.py` (minimal action-trace and prebuilt-agent
modes).
Intent: prove exact champion behavior whenever picker starts are disabled,
before interpreting any competitive result.

Timeout diagnosis: the exact seed 31001 candidate-seat-0 matchup completed
serially without `--diagnostic-json` in about 45 seconds and completed serially
with full diagnostic JSON in about 57 seconds (864 turns, 3.4 MiB diagnostic
file). Neither the match nor diagnostic serialization hangs. The old 180-second
failure was parallel CPU/JAX oversubscription; full diagnostics added measurable
overhead but were not independently responsible.

The first action-only comparison of the uncorrected transplant diverged at
seed 31001, seat 0, turn 17: baseline `[0,13,18,2,0]`, candidate
`[0,13,18,0,0]`. The cause was broader than the previously identified edge
exclusion: the transplant had also changed normal rear classification from
`edge <= 1 || degree <= 1` to `degree <= 1` and replaced champion
`tactical_next_logistics` routing with `tactical_next`. Normal logistics now
uses the exact champion expressions; picker eligibility is gated by
`V35_PICKER_ENABLED`, and the picker source is excluded only while an actual
picker is active.

Unit tests: PASS
Build: PASS

Zero-picker action equivalence:
  - seed 31001, both seats: PASS, every emitted action identical
  - seeds 31000..31004, both seats (10 games, jobs=2): PASS, every emitted
    action identical
  - seeds 31000..31019, both seats (40 games, jobs=2): PASS, every emitted
    action identical

Independent harness revalidation at `a5933d50fce85829ac98a64350a20e0b69f7c5ec`
on 2026-08-19 reproduced the formerly failing seed before starting either
batch.  The exact seed-31001 candidate-seat-0 command completed in 14 seconds
without diagnostics (exit 0), and the same command completed in 14 seconds
with `--diagnostic-json` (exit 0, 1.2 MiB trace).  The action-only checker then
passed seed 31001 in both seats serially in 61 seconds, seeds 31000..31004 in
both seats with `--jobs 2` in 237 seconds, and seeds 31000..31019 in both seats
with `--jobs 2` in 916 seconds.  This confirms on the current workspace that
the game, candidate protocol, and diagnostic writer all terminate normally;
the old 180-second failure depended on the old parallel execution load rather
than a stuck match or agent.

No win-rate benchmark was interpreted during this harness repair. Picker
thresholds and the selective gate were not changed.

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
