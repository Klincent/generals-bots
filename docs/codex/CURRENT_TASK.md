# Current Codex task: redesign picker to preserve champion opportunity cost

## Context

Reference champion:

`e50123cee7d924f0d643acd372a5300971f93917`

Runtime-correct picker branch:

`codex/e50123-picker-fix`

The picker crash is fixed and protocol smoke is clean. The best tested picker configuration so far uses threshold 16 and min efficiency 2.0.

Its best 60-game screen versus exact e50123 on seeds 31000..31029, both seats, was:

- 25 W / 6 D / 29 L
- score 0.4667
- 0 errors / 0 illegal actions
- picker: about 5.92 starts, 5.87 completions, 33.25 picker moves, 429.92 units delivered per game
- about 12.93 delivered units per picker move
- candidate land T50/T100/T150/T250: 18.3 / 38.4 / 56.6 / 80.1
- champion land T50/T100/T150/T250: 19.6 / 43.9 / 62.3 / 95.9
- candidate expansion actions: 111.53/game
- champion expansion actions: 140.08/game
- war activity is roughly unchanged

The important diagnosis is that picker logistics are mechanically healthy but strategically too expensive. It consumes about 33 turns/game, while expansion falls by about 29 actions/game and T250 land trails by about 15.8. The problem is not insufficient picker efficiency per move. The problem is **opportunity cost and scheduling priority**.

Do not solve this by only changing the source threshold again. Threshold 20 and min efficiency 2.5 already regressed.

## Primary objective

Redesign the picker so it recovers useful stranded/edge army **without taking ~33 dedicated turns away from the champion's expansion/war pipeline**.

The picker should become an opportunistic/background logistics mechanism rather than a modal state that monopolizes turns while active.

The final candidate must remain picker-only relative to exact e50123. Do not change anti-cycle, 3x3 exploration, castle policy, threat defense or attack architecture.

## Required code diagnosis

Inspect the current `codex/e50123-picker-fix` implementation carefully before changing it.

There is a known high-value lead in the current scheduler: while `picker_.active` and a picker candidate exists, the code effectively schedules the picker candidate directly instead of allowing normal champion priorities to compete. This likely explains why almost every started picker runs to completion and why expansion loses almost one action per picker move.

Prove this with telemetry on representative identical-seed games before changing it.

Specifically instrument / measure:

- how many picker moves occur on turns where a legal expansion candidate existed;
- how many occur on turns where a war/offense candidate existed;
- how many occur within 8 turns before a production tick;
- how many occur while castle funding is urgent;
- how many picker moves replace what the exact champion chose on the same seed/seat/turn;
- classify the champion's displaced action as expansion / war / search / logistics / pass / hard tactical.

Add aggregate telemetry such as:

- `picker_displaced_expansion`
- `picker_displaced_war`
- `picker_displaced_search`
- `picker_used_idle_slot`
- `picker_opportunity_cost_score`

If exact action-by-action baseline shadowing inside one process is too invasive, derive the comparison from paired replay/audit traces offline. Do not change champion behavior merely to collect telemetry.

## Redesign requirements

Implement a **non-monopolizing picker**. Explore the smallest coherent design that satisfies these constraints:

1. Starting a picker must NOT imply that every subsequent turn is automatically a picker move.
2. True HARD actions always win.
3. Expansion must retain the champion's starvation protection. If a useful expansion candidate exists and expansion has been deferred recently, picker must yield.
4. During healthy early/mid expansion, picker should normally move only when the opportunity cost is low.
5. Picker should yield to meaningful war/offense when contact/general information makes war productive.
6. Picker should avoid stealing the last useful action window before production ticks.
7. Picker may remain logically active while paused. Pause is not abort. Resume later if route/state remains valid.
8. Do not reserve the picker source so aggressively that higher-value champion actions from that same source are suppressed. Protect picker continuity only when the alternative action is genuinely lower value.
9. Prefer picker steps that piggyback on useful inward movement already aligned with champion logistics. If the same move would have been a valid rear evacuation / war mobilization / consolidation step, count it as picker progress without creating an additional dedicated action.
10. Consider a bounded picker duty cycle / token budget rather than unconditional modal execution. Example concept: at most one dedicated picker step every N non-HARD turns unless no productive champion candidate exists. Do not hardcode this blindly; test N values with evidence.
11. Completion target need not always be the general itself. A strategically useful handoff point on the attack/front/logistics backbone can terminate the picker earlier if the collected mass is then naturally consumed by champion logic.
12. Preserve route safety, source protection, resumability and all runtime fixes.

The key metric is no longer only `units delivered / picker move`. Also measure `net useful mass delivered per displaced high-value action`.

## Experimental sequence

Work on a new branch:

`codex/e50123-picker-opportunity-v2`

Start from the runtime-correct picker implementation, preserving its crash fix and protocol regression test.

### Experiment 0 — baseline reproduction

Re-run the best current picker (threshold 16, efficiency 2.0) on the same 60-game screen and confirm results are materially consistent with 0.4667 before redesign.

### Experiment 1 — scheduler de-monopolization

Remove the unconditional/modal picker scheduling behavior. Let picker compete in the existing champion scheduler with explicit safeguards for expansion starvation and war opportunity.

Do not alter route geometry or source threshold in this first experiment.

Run 60 games, seeds 31000..31029 both seats.

### Experiment 2 — low-opportunity duty cycle / piggyback

Based on Experiment 1 telemetry, add one coherent mechanism to reduce dedicated picker turns further. Prefer piggybacking or a duty-cycle gate over another mass threshold change.

Run the same 60-game screen.

### Experiment 3 — shorter handoff / strategic sink

Only if still necessary, test terminating the picker at a useful interior/front handoff rather than always carrying the stack all the way to the general. The goal is to reduce picker move count while preserving delivered strategic value.

Run the same 60-game screen.

Do not make more than these three conceptual changes in one task. Keep each as an inspectable commit so attribution is clear.

## Acceptance gates

A candidate is interesting if all are true:

- 0 runtime/protocol errors
- 0 illegal actions
- 60-game score >= 0.48; >= 0.50 preferred
- T100 land no worse than champion by ~3 on average
- T250 land no worse than champion by ~8 on average
- expansion actions materially recover toward champion levels
- war activity does not materially regress
- castle timing does not materially regress
- picker still delivers meaningful mass
- dedicated picker moves fall materially below the current ~33/game, preferably <= 15/game unless displaced-action telemetry proves the extra moves are nearly free

If a 60-game candidate reaches >=0.50 with healthy telemetry, run an independent 120-game confirmation on seeds 32000..32059 both seats.

If it lands in 0.48..0.50, inspect uncertainty and telemetry and decide whether one final small tuning pass is justified before confirmation.

## Required loss forensics

For each tested version, inspect identical-seed losses and report at minimum:

- champion vs candidate land T50/T100/T150/T250
- expansion action delta
- war/offense delta
- picker dedicated moves
- picker moves that displaced expansion/war
- picker idle-slot/piggyback moves
- castles C1/C2 timing/status
- at least 5 representative losses with a short causal label

Do not call a picker variant bad merely because it delivers less total mass. A lower-volume picker that preserves expansion and improves win rate is preferable.

## Deliverables

Append the new experiment results to `docs/codex/RESULTS.md`.

At completion provide:

- branch and final SHA
- exact code-level cause of current opportunity cost
- baseline reproduction W/D/L
- W/D/L and score for each redesign experiment
- confidence intervals
- land/expansion/war/castle telemetry
- picker displaced-action telemetry
- picker moves and delivered mass
- representative loss diagnosis
- recommended picker design
- whether 120-game confirmation was run

Do not create a leaderboard submission unless the confirmed candidate clearly justifies replacing exact e50123.
