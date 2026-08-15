# V3.5 Focused Recovery Validation Report

## Revision

- Branch: `v35-heuristic-rebuild`
- Starting revision: `94dbf8ae66640b4bc197e70544105e16275661a7`
- Recovery implementation commit: `51fed1fdae6c3ca4ecba364c86de9de9a748c691`
- Exact V3.4 reference: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`
- Report revision: the commit containing this document (a commit cannot contain its own SHA without changing that SHA).

## Previous real failure

GitHub Actions run **31843200843** completed 40 games with **0 W / 9 D / 31 L**, score **11.25%**, seat-0 **10.0%**, seat-1 **12.5%**, paired 95% CI **[5.0%, 18.75%]**, zero errors and zero illegal actions. Candidate mean final land was approximately 36 versus approximately 165 for V3.4; all games ended in `SEVERE_DEFICIT`. Decision p99 was approximately 1.26 ms, ruling out infrastructure and latency as root causes.

## Root causes reproduced from production data flow

1. Ordinary mobilization was permanently tier 2 while expansion was tier 3/4, so any live war candidate lexicographically starved production.
2. Every visible enemy-owned cell created contact/front/war mode, including static distant territory.
3. Static one-army enemy garrisons were counted as packets and produced false SMALL_PACKET_SWARM and MULTI_FRONT evidence.
4. Candidate generation called `assignment()`, mutating every hypothetical packet objective and inflating objective/cycle counters.
5. C1 and C2 future costs reduced the same present army pool; C1 was also reserved long before its actual transport latest start.
6. There was no explicit ordinary enemy capture path beyond enemy-general capture and incidental routing.

## Structural recovery changes

- Replaced ordinary tier starvation with persistent action credits for OFFENSE, EXPANSION, SEARCH and LOGISTICS. Credits accrue from desired action shares and are debited only when a category actually acts. Productive expansion has a four-turn anti-starvation bound outside immediate danger. `SEVERE_DEFICIT` raises the expansion share to 62%, removes optional search and halves war allocation.
- Retained hard tiers only for terminal capture, immediate defense, mathematically safe visible capture, and unavoidable castle build/funding.
- Added explicit favorable ordinary capture and penetration candidates. Combat requires `moving_army > defender`, and rejects a capture when a visible adjacent counterattack can immediately destroy the remainder. Losing 5-vs-20 moves are not emitted.
- Split `enemy_seen`, meaningful contact, immediate threat, active front and confirmed war. Front observations now require movement, adjacency/interaction, or a real general threat. Distant static territory does not create war.
- Opponent packet evidence now comes from temporally moving stacks or meaningful stacks of at least six army. Static one-army territory supplies no swarm sample. No-current-evidence decays confidence toward the prior rather than classifying TURTLE/HOARDER.
- Candidate generation is read-only. Packet creation/objective mutation occurs only after selection. Direct executed-action history backs packet history for reverse/short-cycle detection.
- C2 reserves zero current army until C1 is built and C2 reaches its true JIT start. C1 reserves only at its JIT start. Forecast uses a nearest-first minimum sufficient feeder set and does not subtract feeder reserve twice.
- Added per-game `[v35_actions]`, `[v35_land]`, `[v35_budget]`, `[v35_front]`, `[v35_cycles]`, `[v35_logistics]`, and `[v35_timing]` summaries.

## Agent-level tests

`competition/agents/juraj_v35_cpp/test.sh` passes 20 retained core checks and real-Agent scenarios for:

- safe 20-vs-5 enemy capture;
- rejection of unsafe 5-vs-20 combat;
- distant static enemy territory not creating contact/front/war;
- one broad interacting enemy region clustering into one front;
- expansion receiving actions across multiple turns despite an active front;
- severe-deficit recovery allocation producing neutral captures;
- packet creation only for selected actions and persistence across observations;
- confirmed enemy-general belief surviving later fog;
- static one-army territory not triggering swarm confidence.

## Recovery benchmark

The pushed workflow uses the fresh non-heldout range **21300..21319** (20 maps / 40 paired-seat games). The 100-game step remains gated behind the Phase-1 zero-error, zero-illegal, score >=40% assertion.

- New Actions run ID: pending push.
- New W/D/L and score: pending.
- Land snapshots/action distribution/castle turns/front classification/cycle metrics: emitted by the new runtime; pending Actions artifact.
- Forbidden seeds `30000..30499`: not used.

## Remaining risks and next action

The tactical selector is intentionally much smaller than the full V3.4 combat machinery. Castle site acquisition/replanning and merge identity remain partial. The recovery benchmark must establish whether the structural scheduling fix restores land acquisition. If the fresh 40-game score remains below 40%, inspect at least five losses from `games.jsonl`, classify the dominant next failure, repair it, and rerun another fresh nonheldout 20-map range. Do not launch or interpret the 100-game reference unless the gate passes.

## Evidence-driven repair iteration

The first recovery Actions gate, run **31868337537** on `21300..21319`, completed below the 40% gate (100-game step correctly skipped). Artifact download was unavailable in this environment, so the same compiled agents were sampled locally with fresh processes. Two seed-21300 losses exposed a second systemic defect: the broad `distance <= 5` emergency predicate caused 201 and 596 defense actions, 200/593 executed reversals, and 991/3296 repeatedly counted short cycles. Front counts also reached 15/10. This was false emergency defense—not expansion starvation—and explained continued collapse in one seat.

Commit `4bc39db2566ed2a092fe74c9e51b6b03c7971fb5` repairs that evidence: immediate defense now requires a strong enemy within two cells or a tracked moving stack within five; front clustering uses a wider stable conflict region; executed cycle telemetry counts an executed action once instead of once per matching historical edge. A second fresh Actions gate, run **31868967531** on `21400..21419`, was started; result was still in progress when this report update was committed.

### Five representative loss audit

Local paired smoke used already-built binaries, fresh processes, seeds `21300..21305`, zero errors and zero illegal actions. Five losses were inspected:

1. `21300`, seat 0, turn 600 (before emergency repair): healthy land growth (19/48/73/87/107/116/123 through turn 400) but 201 false defense actions and 200 reversals; dominant cause **false defense/cycling**.
2. `21300`, seat 1, turn 745 (before repair): land peaked at 64 on turn 150 then fell to 44 by turn 600; 596 defense actions and 593 reversals; dominant cause **false defense leading to territorial collapse**.
3. `21302`, seat 1, turn 447 (after repair): land reached 141 by turn 400, with 116 expansion and 112 enemy captures; only six defense actions; dominant remaining cause **late tactical loss**, not production starvation.
4. `21304`, seat 1, turn 163 (after repair): land reached 66 by turn 150 with 56 neutral captures; short loss with 14 defense actions; dominant cause **early tactical/general defense**, not economy starvation.
5. `21305`, seat 1, turn 791 (after repair): land reached 187 by turn 600 with 180 neutral and 247 enemy captures; dominant cause **late combat/Deathtouch conversion**, not territorial collapse.

After the emergency repair, local `21302..21304` scored **4 W / 0 D / 2 L (66.7%)**, and `21305` scored **1 W / 0 D / 1 L (50%)**. These eight local games are only smoke evidence, not a replacement for the 40-game gate, but land/action telemetry demonstrates dramatic recovery from mean final land near 36. The remaining concern is excessive front fragmentation (max 9–10 in long games) and late tactical conversion; those should be evaluated from run 31868967531 before further tuning.

## Time-critical V3.5 staged optimization (2026-08-15)

Starting point: `f032dded496cdf2462fd379f15519b5a8fd10bed`.

| Stage | Commit | Change | Fresh smoke | Result / decision |
|---|---|---|---|---|
| 1 | `582a887` | Deterministic productive fallback and classified PASS telemetry | `21500..21509` requested | Fast behavioral tests pass. Local paired execution did not complete in the available window; no score is claimed. Retained because fallback is safety-gated and has an Agent regression scenario. |
| 2 | `acf3cb1` | One-action-per-turn castle transport forecast, JIT slack, deadline telemetry | `21520..21529` requested | Fast tests pass, including summed feeder action work. Paired smoke did not complete; deadline rates remain unverified. Retained as the explicit bottleneck correction. |
| 3 | `fdfa3b9` | V3.4-inspired post-800 terminal touch and adjacent-general threat semantics | `21540..21549` requested | Fast tests pass. Paired smoke did not complete. Retained because the change is narrowly scoped to terminal competition rules. |

The harness used exact V3.4 commit `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.
Attempts used only specified nonheldout stage ranges; JAX match runtime exceeded the
available execution window. Seeds `30000..30499` were never used.

### Selection and gates

Selected code candidate: `fdfa3b9` (Stage 1+2+3). The `21600..21619` 40-game
gate was **not run**, so no W/D/L, confidence interval, PASS, castle, or land
result is claimed. The >=52% condition was not established, hence
`21650..21699` was **not run**.

### Remaining risk / recommendation

Action-aware castle work may preempt more expansion than intended, while the
fallback can alter long-game packet flow despite its one-ply safety checks.
Deadline attainment and post-800 outcomes remain empirically unmeasured. Do
**not** proceed to final heldout: complete the three smokes and 40-game gate,
then run 100 games only if the score meets the documented threshold.


## Targeted frontier-feed and minimum-defense iteration (2026-08-15)

### Revisions

- Starting SHA: `54631b747391f23ac18dbd00aeae8446bd484405`.
- Stage A (persistent productive frontier feed): `906b0afb95268ba0d35492ca05bad71a85be2b26`.
- Stage B (minimum-sufficient general defense): `9d72e4523c1a703281e52bc779aeb499b7a24e0a`.
- Exact V3.4 reference: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.

### Reused-range evidence (not a fresh validation)

The pre-iteration candidate scored **57.0%** over the previously used
`21100..21149` range, with **0 errors** and **0 illegal actions**. This is
explicitly retained only as reused-range context; it is not evidence for the
Stage A+B candidate. The supplied audit did not include W/D/L, seat split,
paired CI, aggregate PASS/frontier-feed/defense actions, or aggregate land
snapshots, so none are inferred here.

### Fresh validation configured

The workflow now runs Phase 1 on `21600..21619` (20 maps / 40 paired games) and
requires zero errors, zero illegal actions, and score >=52%. Only after that
assertion succeeds does it run Phase 2 on `21650..21699` (50 maps / 100 paired
games). The always-running artifact step uploads Phase-1 output even when the
gate fails.

| Metric | Phase 1 (`21600..21619`) | Phase 2 (`21650..21699`) |
|---|---:|---:|
| W/D/L | Pending fresh Actions run | Pending Phase-1 gate |
| Score / seat split | Pending fresh Actions run | Pending Phase-1 gate |
| Paired 95% CI | Pending fresh Actions run | Pending Phase-1 gate |
| PASS rate | Pending artifact | Pending Phase-1 gate |
| Frontier-feed actions | Pending artifact | Pending Phase-1 gate |
| Defense actions | Pending artifact | Pending Phase-1 gate |
| Land snapshots | Pending artifact | Pending Phase-1 gate |
| Errors / illegal actions | Pending fresh Actions run | Pending Phase-1 gate |

No fresh benchmark result is claimed before GitHub Actions executes this
workflow. No final-heldout seed or seed in `30000..30499` is used.
