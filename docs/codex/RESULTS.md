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

The final harness also closes the process-start cancellation race: once any
worker fails, a shared stop signal prevents queued workers from spawning new
matches, and a worker that races with the stop signal immediately terminates
its newly registered process group. This preserves prompt failure even when a
timeout occurs while another worker is between scheduling and process
registration.

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

## 2026-08-19 — selective picker v4 gate

Date: 2026-08-19
Variant: A — relax only the dominant neutral-opportunity economy condition
Branch: `codex/e50123-picker-selective-v4-gate`
Behaviorally correct parent: `bc3fd06`
Baseline commit: `e50123cee7d924f0d643acd372a5300971f93917`
Frozen candidate source commit: `d3c8bd3c340c1f113e82ec4c16e7c8d91a9e4d9b`
Files changed before freezing: `competition/agents/juraj_v35_cpp/main.cpp`

### Gate diagnosis

The original rejecting gate was replayed on seeds 31000..31029 and
32000..32059, both seats. Across 92,134 mass/efficiency-eligible snapshots,
the unconditional rejection counts were:

- maturity: 103;
- land parity: 19,606;
- recent growth: 32,084;
- immediately capturable neutral opportunities: 92,113;
- concentration: 64,616.

The exact overlap histogram was:

```text
32704 neutral+concentration
18066 neutral only
16110 growth+neutral+concentration
 8769 land-parity+growth+neutral+concentration
 6980 land-parity+neutral+concentration
 5560 growth+neutral
 2197 land-parity+neutral
 1645 land-parity+growth+neutral
   38 maturity+neutral
   37 maturity+neutral+concentration
    8 maturity+concentration
    6 maturity+land-parity+concentration
    5 maturity+land-parity+neutral
    5 maturity only
    2 maturity+land-parity
    2 maturity+land-parity+neutral+concentration
```

Only 21 snapshots satisfied the neutral limit, while 18,066 snapshots failed
only that limit. In original evaluation order, first-failure counts were
maturity 103, land parity 19,591, growth 21,670, neutral pressure 50,770, and
concentration 0. This establishes the `<=3` neutral-opportunity limit as the
dominant over-restrictive economy condition; it was measuring the number of
owned cells with some capturable neutral, not three discrete urgent moves.

### Exact selected gate

Variant A keeps all route mass/efficiency/source safety checks and requires:

- turn >=150 or ownership >=35% of all map cells;
- opponent land is zero or our land is at least 80% of opponent land;
- growth >=2 cells/25 turns or >=3 cells/50 turns, waived at 45% ownership;
- top-three owned stack share <55%;
- largest existing owned stack < proposed picker delivery.

The useful-neutral count remains observational telemetry but is not an
acceptance condition. Variant B and Variant C were not developed: Variant A
landed inside the requested activation range, so additional relaxation or a
different positive trigger was unnecessary and would have increased tuning.

### Variant A screen — 31000..31029

- commit: `d3c8bd3c340c1f113e82ec4c16e7c8d91a9e4d9b`;
- games: 60, both seats, identical per-seed RNG derivation;
- W/D/L: 26/14/20; score 0.5500; paired bootstrap 95% CI [0.4750, 0.6250];
- errors / illegal actions: 0 / 0;
- picker starts: 110 (1.833/game), with >=1 start in 47/60 games (78.3%);
- completions / aborts: 102 / 3, with 5 still active at termination;
- dedicated picker moves: 714 (6.49/start), delivered mass: 4,580
  (41.64/start and 6.41/dedicated move);
- land T100/T250: 42.68 / 89.64 (T250 available in 58 games);
- expansion / war actions: 8,144 / 18,321;
- unconditional gate rejection counts over 18,237 eligible snapshots:
  maturity 36, land parity 4,357, growth 6,436, concentration 17,307, and
  observational neutral pressure 18,229;
- sequential first-failure counts in the selected gate order: maturity 36,
  land parity 4,351, growth 4,151, concentration 9,589;
- candidate decision latency: mean per-game p50 1.948 ms, mean per-game p95
  16.756 ms, maximum decision 216.543 ms.

Every one of the 13 zero-picker games was replayed with action traces against
exact e50123. All actions were identical through termination. Active games
were also identical before their first accepted picker start by construction
of the enabled equivalence checker. Variant A was therefore selected on
selectivity, economics, equivalence, and clean competitive behavior—not merely
its 60-game score—and pushed after the successful benchmark.

### Frozen development confirmation — 32000..32059

- frozen source: `d3c8bd3c340c1f113e82ec4c16e7c8d91a9e4d9b` (no tuning);
- games: 120, both seats;
- W/D/L: 50/38/32; score 0.5750; paired bootstrap 95% CI
  [0.5208, 0.6292];
- errors / illegal actions: 0 / 0;
- starts: 280 (2.333/game), >=1 start in 95/120 games (79.2%);
- completions / aborts: 253 / 20, with 7 active at termination;
- dedicated moves: 1,762 (6.29/start), delivered mass: 13,866
  (49.52/start and 7.87/dedicated move);
- land T100/T250: 42.45 / 88.24 (T250 available in 117 games);
- expansion / war actions: 15,930 / 41,055;
- unconditional rejections over 43,239 eligible snapshots: maturity 67, land
  parity 14,705, growth 16,224, concentration 40,828, observational neutral
  pressure 43,226;
- sequential selected-gate first failures: maturity 67, land parity 14,696,
  growth 8,095, concentration 20,101;
- candidate latency: mean per-game p50 1.794 ms, mean per-game p95 12.689 ms,
  maximum 190.477 ms.

All 25 zero-picker games were independently replayed and remained exactly
action-identical to e50123 through termination. The score and meaningful
activation cleared the predeclared holdout threshold, so the untouched 33000
pool was opened without changing source.

### Untouched holdout — 33000..33059

- frozen source: `d3c8bd3c340c1f113e82ec4c16e7c8d91a9e4d9b`;
- games: 120, both seats;
- W/D/L: 49/25/46; score 0.5125; paired bootstrap 95% CI
  [0.4583, 0.5667];
- errors / illegal actions: 0 / 0;
- starts: 252 (2.100/game), >=1 start in 88/120 games (73.3%);
- completions / aborts: 236 / 12, with 4 active at termination;
- dedicated moves: 1,639 (6.50/start), delivered mass: 12,730
  (50.52/start and 7.77/dedicated move);
- land T100/T250: 41.23 / 84.00;
- expansion / war actions: 15,722 / 39,167;
- unconditional rejections over 30,927 eligible snapshots: maturity 40, land
  parity 8,016, growth 11,336, concentration 29,504, observational neutral
  pressure 30,915;
- sequential selected-gate first failures: maturity 40, land parity 8,011,
  growth 7,033, concentration 15,591;
- candidate latency: mean per-game p50 1.786 ms, mean per-game p95 12.073 ms,
  maximum 211.846 ms.

All 32 zero-picker holdout games were independently replayed and remained
action-identical to exact e50123 through termination. No source or threshold
was changed after viewing the holdout. The holdout score is in the predeclared
0.50..0.52 promising range; no submission archive was created.

Decision: **PROMISING BUT UNCONFIRMED**

Known uncertainty: the 33000 confidence interval is wide and crosses 0.50.
The gate is economically selective and the invariant is intact, but the
holdout does not establish a statistically certain improvement.
