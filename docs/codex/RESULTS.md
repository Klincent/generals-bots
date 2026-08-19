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

## 2026-08-18 picker crash repair and tuning

Date: 2026-08-18  
Variant: picker-only repair  
Branch: `codex/e50123-picker-fix`  
Baseline: exact `e50123cee7d924f0d643acd372a5300971f93917`  
Broken parent: `c919246db8d6140638f1000a02bd9bbae8686f1b`

### Crash reproduction and repair

Seed 31000 was reproduced through the real `competition/matchup.py` process protocol. An ASan/UBSan build (`-fsanitize=address,undefined -fno-omit-frame-pointer -g`) reported `std::vector<char>::operator[]` binding/loading through a null pointer, followed by `AddressSanitizer: SEGV` in `Agent::act` at the turn-zero `owned_castle_history_[t]` access. The call chain was `Agent::act` -> `Agent::decide` -> `main`; the protocol then reported that the candidate closed stdout unexpectedly.

The picker diff had removed only the champion's map-sized `owned_castle_history_.assign(n_,0)` and initial-owned-castle scan from `Agent::init()`. A complete initialization audit found `packet_at_`, `last_owner_`, `last_army_`, graph passability, belief, general and castle planning still initialized identically to e50123; no second missing map-sized initialization was found. The repair restores allocation and the initial castle scan, rather than adding a bounds guard, so champion castle recapture remains active.

Regression proof:
- The new real-process stdin/stdout test builds the agent, sends one complete 21x21 observation, requires a successful five-integer action, and exits cleanly.
- The same test fails against broken `c919246` (nonzero process exit/no action) and passes after the repair.
- The repaired protocol cycle also passes under ASan/UBSan.
- Complete core, recovery, picker lifecycle, picker economics tests and release build pass.

Protocol smoke: seeds `31000..31009`, both seats, 20 games: 7/3/10, score 0.4250, 0 errors, 0 protocol errors, 0 illegal actions.

### Competitive screens versus exact e50123

All screens used seeds `31000..31029`, both seats (60 games), identical RNG seeds, and zero errors/illegal actions.

| Iteration | Picker change | W/D/L | Score | Paired 95% CI | p50 / p95 / p99 latency (ms) |
|---|---|---:|---:|---:|---:|
| Runtime repair | Restore castle-history initialization; defaults threshold 12, efficiency 2.0 | 19/13/28 | 0.4250 | [0.3167, 0.5250] | 1.628 / 1.872 / 1.993 |
| Tune 1 | Raise minimum source mass threshold 12 -> 16 | 25/6/29 | **0.4667** | [0.3833, 0.5500] | 1.572 / 1.801 / 1.861 |
| Tune 2 | Raise threshold 16 -> 20 | 18/11/31 | 0.3917 | [0.2833, 0.5083] | 1.561 / 1.904 / 2.007 |
| Tune 3 | Restore threshold 16; raise minimum efficiency 2.0 -> 2.5 | 23/9/28 | 0.4583 | [0.3583, 0.5500] | 1.508 / 1.736 / 1.974 |

Tune 1 was best and is the final configuration (threshold 16, efficiency 2.0). Tune 2 and Tune 3 were reverted. Because the best score is below 0.48 and land is meaningfully degraded, the 120-game confirmation was not run.

### Best-version telemetry and diagnosis

Best Tune 1 candidate versus the champion on the same games:
- Land T50/T100/T150/T250: candidate 18.3/38.4/56.6/80.1; champion 19.6/43.9/62.3/95.9. Candidate losses: 16.9/34.0/53.0/75.5.
- C1/C2: candidate C1 built 18/60, mean turn 337.8; C2 2/60, mean 546.5. Champion C1 20/60, mean 347.6; C2 2/60, mean 604.5. Candidate losses built C1 6/29 (mean 488.8) and no C2.
- Candidate activity: enemy 245.67, war 282.88, search 38.57, expansion 111.53 actions/game. Champion: enemy 257.95, war 282.72, search 31.18, expansion 140.08.
- Picker economics: starts 5.92, completions 5.87, moves 33.25, units delivered 429.92 per game; 12.93 delivered units per picker move; aborts 0.00, blocked ticks 0.07, source-guard rejects 2.25, critical pre-emption moves 0.47, planned mass 400.88 and planned moves 35.98 per game. Lost/depleted aborts were zero.

Representative identical-seed losses include 31000 seat 0, 31001 both seats, 31002 seat 1 and 31003 seat 1. Runtime and lifecycle are healthy: almost every picker completes, abort/thrash counters are essentially zero, and delivered units per move are strongly positive. The competitive weakness is opportunity cost, not failed logistics. The picker consumes about 33 actions/game while candidate expansion falls by roughly 29 actions/game and T250 land trails by 15.8. Raising the threshold to 16 reduced this cost and improved score, but threshold 20 and efficiency 2.5 each worsened results. No unrelated champion strategy was changed.

Decision: **RUNTIME FIXED; COMPETITIVELY REJECTED**. Keep exact e50123 as champion. The final picker-fix branch is non-crashing and inspectable, but it does not satisfy the replacement gate and should not receive a leaderboard submission.

## 2026-08-18 picker opportunity-cost redesign v2

Baseline remains exact `e50123cee7d924f0d643acd372a5300971f93917`. All screens use seeds `31000..31029`, both seats, identical `JURAJ_RNG_SEED`, and the real `competition/matchup.py` protocol. The candidate remains picker-only and retains the repaired map-sized castle-history initialization and real-process protocol regression test from `705fb94`.

### Experiment 0 — threshold-16 / efficiency-2.0 reproduction

Branch/commit: `codex/e50123-picker-fix` / `705fb94`. The completed 60-game reproduction recorded immediately before this redesign is 25/6/29, score 0.4667, paired bootstrap 95% CI [0.3833, 0.5500], 0 errors and 0 illegal actions. Candidate land was 18.3/38.4/56.6/80.1 at T50/T100/T150/T250 versus champion 19.6/43.9/62.3/95.9; expansion was 111.53 versus 140.08 actions/game. Picker economics were 5.92 starts, 5.87 completions, 33.25 moves, 429.92 units delivered, and 12.93 delivered units/move. This confirms that the modal branch's healthy mechanics nevertheless displaced growth.

### Experiment 1 — champion scheduler competition

Branch/commit: `codex/e50123-picker-opportunity-v2` / `b1edc4015f5e0a9f8c4f306e458e0d64d849d734`.

Change: removed the direct `picker_.active && picker_available` selection path and aggressive source reservation. HARD candidates and the unmodified champion `strategic_pick` now decide every turn; an active picker can pause without aborting. Added opportunity telemetry for expansion/offense availability, the final eight pre-production turns, urgent castle funding, idle slots, and pauses.

Screen: 28/6/26, score 0.5167, paired bootstrap 95% CI [0.4083, 0.6250], 0 errors, 0 illegal actions. Six disjoint benchmark chunks were run concurrently after prebuilding immutable agent snapshots; aggregate game-level round-trip p50 was about 3.7 ms and chunk p95 ranged 4.1–5.8 ms (concurrency inflates these relative to candidate-internal p50/p95/p99 0.50/0.83/3.51 ms).

Telemetry: land 18.30/38.45/57.20/80.98; expansion 113.15, war 270.35, enemy 236.82, search 39.10 actions/game. C1 built 20/60 (mean turn 295.1), C2 2/60 (mean turn 245). Picker: 6.28 starts, 5.63 completions, 31.75 moves and 407.32 delivered units/game (12.83 units/move). Of those moves, only 0.33/game had an expansion candidate and none had an offense candidate; 2.25 were within eight turns of production, none coincided with an urgent castle candidate, and 31.42 were classified as idle slots with neither expansion nor offense available. The picker was logically paused 20.98 candidate turns/game.

Diagnosis: direct modal monopolization was real in Experiment 0, but removing it did not restore land: the picker still changed the board on roughly 32 nominally idle logistics/search slots, which changes later candidate availability. The exact champion's counterfactual action cannot be recovered from the existing audit format after states diverge (the audit stores results, latency and legality, not per-turn candidate classifications); the in-state classifier establishes that almost all selected picker actions displaced lower-priority search/logistics/pass rather than a simultaneously legal expansion or offense candidate.

### Experiment 2 — low-opportunity duty cycle

Branch/commit: `codex/e50123-picker-opportunity-v2` / `7c1d1fad370eac29c45ec2528bc07854538caa3e`.

Change: one coherent duty-cycle gate: when productive champion work exists, picker yields to offense, expansion starvation, urgent castle funding, the final eight turns before production, and a minimum three-turn spacing. Logical picker state is retained while paused. No geometry or threshold changed.

Screen: 28/6/26, score 0.5167, paired bootstrap 95% CI [0.4083, 0.6250], 0 errors, 0 illegal actions. Candidate-internal p50/p95/p99 was 0.49/0.91/3.41 ms. Land 18.30/38.45/57.20/80.98; expansion 113.27, war 274.88, enemy 242.47, search 39.10. C1/C2 results were unchanged at 20/60 (295.1) and 2/60 (245). Picker: 6.38 starts, 5.73 completions, 33.30 moves, 417.83 delivered (12.55 units/move), 14.00 duty yields and 22.42 paused turns/game. Selected picker moves with expansion/offense/near-tick/urgent-castle candidates were 0.27/0/2.33/0; 33.03 were idle-slot moves.

Diagnosis: the duty gate fired, but the explicit idle-slot bypass meant it did not reduce the dominant cost. This experiment is attribution evidence against keeping that bypass, not a successful reduction in dedicated volume.

### Experiment 3 — safe interior handoff

Branch/commit: `codex/e50123-picker-opportunity-v2` / `96063b069b6c642f6ebf4ba637eedaf3ee8845b2`.

Change: retain Experiment 2 and complete a picker at a safe owned cell three tiles inside the edge rather than requiring every collected stack to traverse all the way to the general. The handoff remains available to unchanged champion logistics/war logic.

Screen: 29/6/25, score 0.5333, paired bootstrap 95% CI [0.4333, 0.6333], 0 errors, 0 illegal actions. Candidate-internal p50/p95/p99 was 0.50/0.79/3.84 ms. Land 18.30/38.45/57.20/80.98; expansion 113.27, war 277.32, enemy 247.65, search 39.10. C1 built 21/60 (mean 321.3), C2 2/60 (mean 245). Picker: 6.43 starts, 5.80 completions, 32.17 moves, 415.28 delivered (12.91 units/move), 13.68 duty yields and 22.03 paused turns/game. Selected picker moves with expansion/offense/near-tick/urgent-castle candidates were 0.22/0/2.27/0; 31.95 were idle-slot moves.

Representative losses include seed/seat 31010/0, 31012/0, 31013/0, 31014/0, 31015/1, 31016/1, 31017/0 and 31018/0. Across these and the aggregate, early and late land remain the principal failure: T100 trails the champion reference by about 5.5 and T250 by about 14.9, expansion remains about 27 actions/game below the champion, and dedicated picker volume remains far above the requested 15 despite healthy completion/economics. War activity is not materially below the earlier picker, castles do not collapse, and no runtime/lifecycle failure is present.

Decision: **DO NOT CONFIRM; KEEP e50123 CHAMPION.** Experiment 3 has the best point score, but it fails the explicit land, expansion, and dedicated-move health gates, and its wide interval includes substantial regression. Therefore the independent 120-game confirmation and leaderboard submission are not justified. Recommended picker design direction is the non-modal scheduler integration from Experiment 1, but with the idle-slot bypass removed or true piggyback recognition added so a picker progresses only when the champion-selected move itself advances the collector. A shorter handoff alone is insufficient.
## 2026-08-19 picker Experiment 3 independent confirmation

Date: 2026-08-19
Variant: Experiment 3 opportunistic picker with safe interior handoff
Branch: `codex/e50123-picker-opportunity-v2`
Tested candidate commit: exact `96063b069b6c642f6ebf4ba637eedaf3ee8845b2`
Baseline commit: exact `e50123cee7d924f0d643acd372a5300971f93917`
Files changed for the confirmation: none before or during the run; this results section was appended only after all 120 games completed.
Intent: independently determine whether the candidate's 29/6/25 (0.5333) screen on seeds 31000..31029 was a real improvement or screening noise. Lower land was treated as diagnostic rather than an automatic rejection.

Unit tests: PASS (`bash competition/agents/juraj_v35_cpp/test.sh`: core, agent-recovery, picker-lifecycle, picker-economics, and real protocol tests passed)
Build: PASS for both the candidate and an exact detached worktree of the champion.

Confirmation benchmark:
- Protocol: `competition/agents/juraj_v35_cpp/paired_benchmark.py`, competition mode, seeds `32000..32059`, both seats, identical per-map `JURAJ_RNG_SEED=(seed*0x9E3779B1+0x35)&0xffffffff`; no tuning, source edits, early stopping, or intermediate-result changes.
- Games: 120 (60 paired maps)
- W/D/L: **37/18/65**
- Score: **0.3833** (`(37 + 0.5*18)/120 = 46/120`)
- Paired bootstrap 95% CI: **[0.3125, 0.4542]** (10,000 seed-pair resamples)
- Seat scores: candidate seat 0 = 0.4083; candidate seat 1 = 0.3583
- Errors / illegal actions: **0 / 0**
- Mean game length: 834.66 turns
- Candidate decision round-trip latency: game-p50 distribution p50/p95/p99 = 1.162/1.376/1.414 ms; maximum individual game-level decision maximum = 130.551 ms. Candidate self-timing means were p50/p95/p99/max = 0.349/0.550/1.426/12.190 ms; champion self-timing means were 0.330/0.538/1.251/11.924 ms.

Aggregate telemetry (candidate versus champion):
- Land T50/T100/T150/T250: **17.18/35.67/51.87/74.31** versus **19.40/42.83/62.38/95.67**. T150 and T250 means include only games reaching those snapshots; early decisive games legitimately omit later snapshots.
- Expansion actions: **117.53 versus 145.55/game**.
- Enemy/offense actions: **284.10 versus 300.95/game**.
- War-mobilization actions: **307.71 versus 307.54/game** (essentially unchanged).
- Search actions: **31.77 versus 30.53/game**.
- Rear/logistics actions: **46.38 versus 30.97/game**.
- C1: candidate built 49/120, mean build turn 342.71; champion 41/120, mean 307.78.
- C2: candidate built 15/120, mean build turn 722.33; champion 8/120, mean 509.50. The candidate built somewhat more castles but later; castle urgency never directly coincided with a selected picker move.
- Meaningful enemy contact: 116.65 versus 116.64 mean turn; max active fronts 9.27 versus 8.95. There is no aggregate evidence of faster enemy-general pressure.
- Picker starts/completions/moves: **6.03/5.34/29.77 per game**.
- Picker delivered mass: **257.53 units/game**; **8.65 delivered units per picker move**.
- Picker aborts: 0.58/game (0.57 depleted, 0.01 lost); active at termination 0.12/game; blocked ticks 0.10/game; critical pre-emption moves 0.50/game.
- Picker scheduling: 29.67 idle-slot moves, 0.10 moves with expansion available, 0 with war available, 1.26 within eight turns of production, 0 with urgent castle funding, 29.88 pauses, and 20.06 duty yields per game. Thus most picker steps satisfy the low-opportunity scheduler definition, but their route/lifecycle still correlates with 28 fewer expansion actions and a 21.36-cell T250 deficit.

Concentration and conversion forensics:
- Army totals and packet concentration are not retained by the normal compact audit. After the complete confirmation (never during it), the exact binaries, seeds, seats, and RNG values were replayed with the runner's diagnostic-state output for three representative wins and three losses. “Top 3” is the sum of the three largest owned stacks; “scattered” counts owned units in stacks of at most three. These are diagnostic replays, not additional scored games.
- **Win 32029, seat 1 (turn 143):** the candidate delivered 133 units in 15 picker moves. At T100 it held only 29 land and 98 total army versus the opposing champion's 50 land and 121 army, but its largest stack was **41 versus 10**, its top-three share was **46.9% versus 19.8%**, and it had only 57 units in small scattered stacks versus 97. The concentrated packet converted a severe territorial deficit into a very early general capture.
- **Win 32054, seat 1 (turn 841):** seven completed pickers delivered 429 units in 32 moves. At T250 the candidate had 50 land/248 total army versus 89/323, yet fielded a **107-unit maximum stack and 117 top-three mass** versus 31 and 68. This is the clearest positive case: picker concentration produced a credible decisive packet even with much lower breadth. In the paired same-seed/seat counterfactual, the champion had T100/T150/T250 land 47/67/79 versus the winning candidate's 39/50/50, but did not obtain this candidate win.
- **Win 32059, seat 1 (turn 1198):** seven pickers delivered 195 units in 40 moves. The candidate's same-seat trace had 466 enemy and 454 war actions, versus 249 and 282 for the champion on the paired same-seed/seat run, and meaningful contact at turn 75 versus 89. At T600 in the direct game it had 789 total army versus 590. This supports better war conversion in this individual win, although its T800 top-three share was only 4.7%, so not every win is explained by permanent concentration.
- **Loss 32008, seat 0 (turn 1172):** 13 completions, 94 picker moves, and 521 delivered units produced a T800 maximum stack of 115 versus 72 and top-three share 24.0% versus 11.1%, but total army was only 826 versus 1283 and land 105 versus 184. Concentration did not compensate for the much smaller economy; this is an overactive-picker/economic-deficit loss.
- **Loss 32022, seat 1 (turn 793):** only one two-move picker delivered 18 units. The candidate began in a severe growth stall (T50/T100 land 3/5 versus 19/44 directly) and accumulated very high concentration because it owned almost no territory; at T600 it had 422 total army versus 1358. This is not evidence that the picker displaced expansion, and concentration was strategically unusable.
- **Loss 32027, seat 1 (turn 188):** no picker started. Land was tied at T50 and the candidate led directly at T100 (39 versus 36), but it lost shortly after contact; this is an early tactical/defensive conversion loss rather than a picker-volume loss.

Interpretation:
- The requested non-land hypothesis is real in some wins: Experiment 3 can turn a smaller territorial base into substantially larger attack packets, reduce low-value scattered mass, and win by decisive general pressure (especially seeds 32029 and 32054).
- It is not reliable enough in aggregate. Candidate war activity was flat, enemy/offense activity was lower, meaningful contact was not earlier, and the economy/land deficit often reduced total army more than concentration improved usable packet size. The representative losses include both excessive logistics (32008) and failures where picker did essentially nothing (32022/32027), so there is no single automatic “lower land” rejection; the competitive result itself rejects the experiment.
- The confirmation score is 15 percentage points below even 0.50, the entire paired 95% interval lies below 0.48, and the candidate lost 28 more games than it won. The earlier 0.5333 screen was screening noise rather than a reproducible edge.

Decision: **REJECT EXPERIMENT 3** under the explicit `<0.48` rule. Keep exact `e50123cee7d924f0d643acd372a5300971f93917` as champion. Do not recommend larger final validation or submission consideration. Runtime is healthy, but Experiment 3 does **not** beat e50123 on independent seeds.
