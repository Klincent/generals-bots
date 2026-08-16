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

## Stage A isolation test

Stage B was reverted to isolate Stage A without changing strategy. A direct
production-code comparison with the Stage A commit is empty for `main.cpp` and
`core.hpp`, confirming that the tested agent retains productive frontier feed
but not the minimum-sufficient general-defense change.

### Revisions

- Starting HEAD: `21a9594dc4228170600b327c7c169f342b04f611`.
- Stage-B revert: `62e96b7ade40665ba3b979329ecc4284e16ed51a` (`Revert "v35: plan minimum sufficient general defense"`).
- Final tested SHA: `9b628f91143787e48586b91a4ccc22d22b57a572`.
- Exact V3.4 baseline: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.

### Fresh Phase 1 (`21700..21719`)

The workflow always completes all 20 maps / 40 paired-seat games, checks for
zero errors and illegal actions, and uploads the benchmark artifact. Phase 2
is gated on a Phase-1 score of at least 52% plus technical health.

| Metric | Phase 1 |
|---|---:|
| W/D/L | 13 / 5 / 22 |
| Score | 38.75% |
| Seat 0 / seat 1 | 40.0% / 37.5% |
| Paired 95% CI | [27.5%, 50.0%] |
| Errors / illegal actions | 0 / 0 |
| PASS count / rate | 247 / 0.864% of 28,601 turns |
| Frontier-feed actions | 5,053 (2,711 assignments; 2,625 completed) |
| Defense actions | 455 |
| Land snapshots | mean 21.10 @50; 33.73 @100; 40.77 @150; 52.15 @200; 65.83 @250; 79.47 @300; 98.79 @400; 138.12 @600; 175.62 @800 |

GitHub Actions run `31909970537` completed Phase 1 and uploaded the artifact.
The 38.75% result is below the 45% diagnostic threshold, so Stage A is
probably also harmful. This is a causal-isolation result only; no strategy or
constant was changed in response.

### Optional Phase 2 (`21750..21799`)

The 50-map / 100-game phase was correctly skipped because Phase 1 did not
reach the 52% score gate. No Phase-2 W/D/L or other result is claimed. No seed
in the final-heldout `30000..30499` range was used.

## Pre-Stage-A/B candidate fresh validation

### Revisions and equivalence proof

- Starting HEAD: `430e0829dffa476bf8fd0d443ed2d1e4f9250fe6`.
- Stage-A revert: `11022908c6d42c990021ee067848b4dce50b606b`
  (`Revert "v35: keep surplus moving toward productive frontiers"`).
- Final tested SHA: `af17634f006b793e63afdc19ef893d57eedf6636`.
- Pre-Stage-A/B reference: `54631b747391f23ac18dbd00aeae8446bd484405`.
- Exact V3.4 baseline: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.

The following production-code comparison produced no output, proving that the
tested `main.cpp` and `core.hpp` match the pre-Stage-A/B gameplay source:

```text
git diff 54631b747391f23ac18dbd00aeae8446bd484405 -- \
  competition/agents/juraj_v35_cpp/main.cpp \
  competition/agents/juraj_v35_cpp/core.hpp
```

Only the validation workflow changed between the revert and the tested SHA.
No gameplay was modified in response to either fresh result.

### Fresh Phase 1 (`21800..21819`)

Phase 1 covered 20 maps / 40 paired-seat games. GitHub Actions run
`31932565202` passed the technical-health and 52% score gate, so Phase 2 ran
automatically. A deterministic local replay was used to aggregate the retained
per-game telemetry; its complete result matched the Actions gate outcome.

| Metric | Phase 1 |
|---|---:|
| W/D/L | 19 / 7 / 14 |
| Score | 56.25% |
| Seat 0 / seat 1 | 55.0% / 57.5% |
| Paired 95% CI | [45.0%, 67.5%] |
| Errors / illegal actions | 0 / 0 |
| Turns | 31,308 total; 782.70 mean/game |
| Decision timing | p50 1.53 ms; p95 1.81 ms; p99 1.90 ms; max 54.09 ms (local replay) |
| PASS count / rate | 551 / 1.760% of turns |
| Defense actions | 253 |
| Castle actions / completed castle records | 27 / 17 across 15 games |

Mean land snapshots (with the number of games reaching each snapshot in
parentheses): **17.93 @50 (40), 40.58 @100 (40), 59.02 @150 (40), 76.92 @200
(40), 92.26 @250 (39), 104.39 @300 (38), 126.21 @400 (34), 169.54 @600
(28), and 206.90 @800 (21)**.

This 56.25% result is above the strong 55% diagnostic threshold on Phase 1.

### Automatic Phase 2 (`21850..21899`)

The Phase-1 gate correctly started the 50-map / 100-game extension. The games
completed, but the health assertion failed because three candidate illegal
actions were recorded. This is reported as measured; no strategy, constant,
or gameplay response was made.

| Metric | Phase 2 |
|---|---:|
| W/D/L | 53 / 6 / 41 |
| Score | 56.0% |
| Seat 0 / seat 1 | 61.0% / 51.0% |
| Paired 95% CI | [46.5%, 65.5%] |
| Errors / illegal actions | 0 / 3 |
| Turns | 64,968 total; 649.68 mean/game |
| Decision timing | p50 1.53 ms; p95 1.72 ms; p99 1.79 ms; max 64.10 ms (local replay) |

The Phase-2 technical-health requirement was therefore **not** met despite the
56.0% score. No seed in the protected `30000..30499` range was used.

## V3.5 technical-health and loss-conversion iteration (2026-08-16)

### Revisions and selected candidate

- Starting HEAD: `bfdadb47b88e2607f83b34395cf9a80b7fd7efce`.
- Gameplay-equivalent reference: `54631b747391f23ac18dbd00aeae8446bd484405`.
- Exact V3.4 baseline: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.
- Live-cost/legality commit: `ad9515c92cad83a20825a3a7fe69cc70b4ec1f88`.
- Narrow recovery commit: `67672295b590b8d2ba6962ce30905c6bc7a6d0a3`.
- Selected candidate at report time: `67672295b590b8d2ba6962ce30905c6bc7a6d0a3`.

### Illegal-action root cause and correction

A deterministic replay used seed 21891, candidate seat 0, competition RNG seed
1640696520. At the starting HEAD it reproduced the original 435-turn loss,
three candidate illegal actions, five emitted castle actions, and two completed
castles. Thus all three illegals are exactly the three emitted BUILD actions
which the engine rejected (the only discrepancy between emitted castle actions
and completed builds). The old deadline telemetry still reported both planned
prices as 35 after C1 existed.

The corrected replay produced zero illegal actions. Runtime pricing now scans
the observation for every currently owned general/castle and applies the exact
Manhattan surcharge. Forecast requirements, hard reservations, eligibility,
reported C1/C2 prices, and final emission validation all use that current
price. A final guard also checks bounds, ownership, plain type, non-general,
non-castle, and sufficient observed army. Telemetry counts positions where the
old static check would have emitted BUILD but the live check blocks it.

### Full Phase-2 loss split

The retained 100-game result contains 53 wins, 6 draws, and 41 losses. Applying
`land100 < 30 AND PASS > 5%` gives exactly 17 early-stall losses and 24
healthy-economy tactical losses. No win satisfies either individual condition.

| Cohort | Games | land50 | land100 | land150 | land200 | PASS rate |
|---|---:|---:|---:|---:|---:|---:|
| Early-stall losses | 17 | 4.06 | 6.94 | — | — | 39.8% |
| Healthy losses | 24 | 19.33 | 42.54 | 61.25 | 77.46 | 1.2% |
| Wins | 53 | 19.55 | 42.32 | 60.36 | 77.23 | 0.7% |

Seventeen healthy losses ended by turn 500 and seven ended later. Mean defense
action rate was approximately 2.6% in healthy losses versus 0.6% in wins. This
supports investigation, not a broad defense rewrite.

### Tactical forensics status and recurring causes

The requested action-level replay/classification of the 17 representative
healthy losses was not completed in this time-limited local run. Consequently
no tactical cause count is asserted and no tactical gameplay change was made.
This is deliberately recorded rather than inventing classifications without
the last-30-action evidence. The representative table and recurring-cause count
remain an explicit follow-up risk.

### Narrow otherwise-PASS recovery

Recovery runs only after the normal scheduler and the unchanged fallback order
(enemy, neutral, persistent, rear, consolidate, explore) are empty for two
consecutive turns. It is disabled during immediate general threat, hard castle
funding, and from turn 250 onward. It excludes the general, uses only surplus
above `reserve()`, travels one cycle-safe step through owned territory toward a
neutral/fog frontier, and yields immediately when any normal action returns.
Only one recovery target can exist. Trigger/action/completion/normal-abort and
maximum would-PASS streak telemetry are emitted alongside the original PASS
counters.

### Validation status

The exact diagnostic replay of 21891 is not fresh validation and is reported
only as root-cause evidence. A Phase-1 attempt began on 21900 and completed the
paired games for 21900..21903 plus one game for 21904 before the local run was
stopped; this incomplete sample is intentionally not scored or claimed as the
required 40-game gate. Therefore Phase 1 and Phase 2 are **not complete**, and
no W/D/L, CI, aggregate health statistic, or score gate is claimed. The final
heldout range 30000..30499 was not used.

### Exact remaining risks

1. The recovery commit has deterministic agent tests but has not passed the
   required complete fresh 40-game score/health gate; it must be reverted if
   that gate scores below 50%, and should be treated conservatively at 50–54%.
2. Seeds 21900..21904 have now been touched and cannot be presented as wholly
   fresh validation in a resumed run; use a new nonheldout range.
3. The complete 41-loss artifact audit and representative tactical
   classifications remain unfinished; no tactical fix is justified yet.
4. Dynamic pricing can reserve more army and delay C2 relative to the old,
   illegal behavior. This is necessary technical correctness but remains a
   gameplay-score risk.

## V3.5 fresh health/recovery validation (2026-08-16)

### Revisions and evidence separation

- Tested workflow SHA: `452fc1d146732d7ee503d854a5ca9e92792ab191`.
- Selected gameplay commit: `67672295b590b8d2ba6962ce30905c6bc7a6d0a3`.
- Mandatory live-cost fix: `ad9515c92cad83a20825a3a7fe69cc70b4ec1f88`.
- Exact V3.4 baseline: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.
- Fresh GitHub Actions run: `31952572211`.
- Preserved fresh artifact: `v35-reference-validation` (artifact `9265524313`,
  SHA-256 digest
  `8d85a98dbc621dc7094c8bd459d9bc8b8ed2b8d00f4ca4c4639cc3fb90e0d5ed`).

The fresh Actions run completed successfully. Therefore Phase 1 met all three
workflow gates (score at least 54%, zero errors, and zero illegal actions),
Phase 2 ran automatically, and its zero-error/zero-illegal health assertion
also passed. The complete artifact is retained for the requested future
tactical-loss audit. A deterministic local replay of the same candidate,
baseline, maps, seats, and RNG seeds supplied the detailed aggregates below;
it is analysis of the fresh run, not an additional fresh seed claim.

### Fresh Phase 1 (`22000..22019`)

Phase 1 covered 20 maps / 40 paired-seat games and cleared the 54% automatic
continuation gate.

| Metric | Result |
|---|---:|
| W / D / L | 21 / 3 / 16 |
| Score | 56.25% |
| Seat 0 / seat 1 | 70.0% / 42.5% |
| Paired bootstrap 95% CI | [40.0%, 72.5%] |
| Errors / illegal actions | 0 / 0 |
| PASS count / rate | 1,171 / 3.916% of 29,903 turns |
| Stall triggers / actions | 22 / 22 |
| Stall completed / normal-action aborts | 18 / 4 |
| Maximum consecutive would-PASS | 49 |
| Live-cost prevented invalid builds | 0 |
| Defense actions | 501 |
| Castle actions / castles completed | 23 / 23 |

Mean candidate land was **15.93 @50 (40 games), 35.02 @100 (40), 53.15
@150 (40), and 74.08 @200 (39)**. Eight games had land100 below 30, eight
had PASS rate above 5%, and the same eight met both conditions. All eight of
the combined-condition games were losses.

### Fresh Phase 2 (`22050..22099`)

Phase 2 covered 50 maps / 100 paired-seat games. Its 54.0% score is
**acceptable** under the specified interpretation, and both hard health
requirements passed.

| Metric | Result |
|---|---:|
| W / D / L | 45 / 18 / 37 |
| Score | 54.0% |
| Seat 0 / seat 1 | 59.0% / 49.0% |
| Paired bootstrap 95% CI | [46.0%, 62.0%] |
| Errors / illegal actions | 0 / 0 |
| PASS count / rate | 1,967 / 2.649% of 74,250 turns |
| Stall triggers / actions | 35 / 35 |
| Stall completed / normal-action aborts | 28 / 7 |
| Maximum consecutive would-PASS | 49 |
| Live-cost prevented invalid builds | 0 |
| Defense actions | 827 |
| Castle actions / castles completed | 53 / 53 |

Mean candidate land was **17.04 @50 (100 games), 37.75 @100 (100), 55.70
@150 (100), and 72.72 @200 (99)**. Fourteen games had land100 below 30,
twelve had PASS rate above 5%, and twelve met both conditions. Eleven of the
twelve combined-condition games were losses.

The prior fresh Phase-2 reference had **17 of 41 losses** meeting the combined
early-stall condition. The new phase has **11 of 37 losses**, a reduction of
six such losses in absolute count and from 41.5% to 29.7% as a share of losses.
This is consistent with the narrow recovery reducing the targeted failure
mode while the overall score remains at the acceptable threshold. It is not a
tactical-cause classification: the artifact must be preserved and the 37
losses audited before any tactical code is changed.

### DIAGNOSTIC REPLAY / USED SEEDS

Actions run `31951877460` tested the already-used `21800..21819` and
`21850..21899` ranges at SHA
`357401b9590fb62e3ff0dedd4c8635d9058fb71f`. It completed successfully, so
both phases had zero errors and zero illegal actions and seed 21891 was
technically clean in this replay. This supports the live-cost fix's technical
effect, but it is **not fresh validation**, contributes no games or telemetry
to the `220xx` tables above, and is not used to assess the recovery score.

No seed in `21900..21904` or the protected final-heldout range
`30000..30499` was used for this validation. No submission archive was
created, and no gameplay was changed after either phase.
## Recovery exact-seed A/B (used diagnostic seeds; not fresh validation)

- Variant C: `ad9515c92cad83a20825a3a7fe69cc70b4ec1f88`.
- Variant R: `67672295b590b8d2ba6962ce30905c6bc7a6d0a3`.
- Exact V3.4: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.
- Used range: `22050..22099`, 50 maps / 100 paired-seat games.
- Both local variants were materialized with `git archive` at the exact commit; the baseline, engine, truncation, seat order, and `seed * 0x9E3779B1 + 0x35` RNG derivation were identical.

| Variant | W | D | L | Score |
|---|---:|---:|---:|---:|
| C | 45 | 18 | 37 | 54.00% |
| R | 45 | 18 | 37 | 54.00% |

### Match-by-match flip matrix

| C to R | Games |
|---|---:|
| draw->draw | 18 |
| loss->loss | 36 |
| loss->win | 1 |
| win->loss | 1 |
| win->win | 44 |

Recovery added **+0.0 points**: 1 improved, 1 regressed, and 98 unchanged games.

| Seat | Net points | Improved | Regressed |
|---:|---:|---:|---:|
| 0 | -1.0 | 0 | 1 |
| 1 | +1.0 | 1 | 0 |

### Early-stall causal transitions

| C to R | Games | Net points | Improved | Regressed |
|---|---:|---:|---:|---:|
| early-stall->early-stall | 12 | +0.0 | 1 | 1 |
| healthy->healthy | 88 | +0.0 | 0 | 0 |

**Recovery recommendation: UNPROVEN.** Prefer the simpler castle-only C candidate; recovery produced one improvement and one regression and did not cure an early-stall game. The mandatory live castle-cost fix remains required regardless of this decision.

## Phase-2 loss forensics

The table audits all 37 losses from the deterministic R replay. Classifications are based on protocol-visible state/action facts; the tooling explicitly marks internal candidate/objective facts that production does not emit as unobservable.

| Seed | Seat | Turn | Early stall | Primary cause | Evidence |
|---:|---:|---:|:---:|---|---|
| 22050 | 0 | 516 | yes | EARLY_STALL | land100=5; PASS=24.6% |
| 22050 | 1 | 829 | yes | EARLY_STALL | land100=3; PASS=15.9% |
| 22051 | 0 | 584 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=25; final threat-general margin=27 |
| 22052 | 0 | 767 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=5; final threat-general margin=14 |
| 22052 | 1 | 801 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 30-turn warning |
| 22053 | 0 | 420 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 30-turn warning |
| 22054 | 1 | 610 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 28-turn warning |
| 22055 | 1 | 750 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=9; final threat-general margin=78 |
| 22056 | 0 | 814 | yes | EARLY_STALL | land100=9; PASS=13.5% |
| 22056 | 1 | 464 | yes | EARLY_STALL | land100=5; PASS=26.9% |
| 22058 | 0 | 639 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 30-turn warning |
| 22060 | 0 | 807 | no | ECONOMICALLY_OUTPLAYED | no locally winning interceptor/counter-race observed; land100=46 |
| 22062 | 1 | 634 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=5; final threat-general margin=19 |
| 22064 | 1 | 320 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=7; final threat-general margin=16 |
| 22066 | 0 | 688 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 5-turn warning |
| 22067 | 1 | 243 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 26-turn warning |
| 22069 | 1 | 1107 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=7; final threat-general margin=98 |
| 22071 | 0 | 443 | yes | EARLY_STALL | land100=5; PASS=28.7% |
| 22072 | 1 | 444 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 30-turn warning |
| 22075 | 0 | 393 | yes | EARLY_STALL | land100=6; PASS=31.8% |
| 22075 | 1 | 521 | yes | EARLY_STALL | land100=5; PASS=23.6% |
| 22076 | 0 | 355 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 30-turn warning |
| 22078 | 1 | 720 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=23; final threat-general margin=7 |
| 22079 | 0 | 570 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=20; final threat-general margin=4 |
| 22079 | 1 | 211 | yes | EARLY_STALL | land100=5; PASS=60.7% |
| 22081 | 0 | 277 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 29-turn warning |
| 22081 | 1 | 170 | no | INTERCEPT_AVAILABLE_NOT_USED | legal winning adjacent interceptor observed; 30-turn warning |
| 22082 | 0 | 788 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=7; final threat-general margin=32 |
| 22083 | 1 | 915 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=14; final threat-general margin=7 |
| 22086 | 1 | 738 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=5; final threat-general margin=25 |
| 22087 | 1 | 348 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=9; final threat-general margin=32 |
| 22089 | 1 | 570 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=30; final threat-general margin=10 |
| 22094 | 0 | 202 | yes | EARLY_STALL | land100=7; PASS=72.8% |
| 22095 | 1 | 784 | yes | EARLY_STALL | land100=7; PASS=16.5% |
| 22096 | 1 | 255 | no | DEFENSE_UNDERCOMMITTED | visible threat warning=5; final threat-general margin=21 |
| 22098 | 0 | 788 | no | MISSED_COUNTERATTACK | known enemy general had a nearby stronger friendly stack |
| 22099 | 1 | 575 | yes | EARLY_STALL | land100=5; PASS=23.3% |

### Primary-cause counts

| Cause | Losses |
|---|---:|
| DEFENSE_UNDERCOMMITTED | 14 |
| EARLY_STALL | 11 |
| INTERCEPT_AVAILABLE_NOT_USED | 10 |
| ECONOMICALLY_OUTPLAYED | 1 |
| MISSED_COUNTERATTACK | 1 |

Recurring observed classes (at least five losses): **DEFENSE_UNDERCOMMITTED (14)**, **EARLY_STALL (11)**, **INTERCEPT_AVAILABLE_NOT_USED (10)**.
No gameplay correction is implemented here. A class count alone does not satisfy the required local-correction and Agent-test gates.

### Comparable-win controls and next-correction gate

Three winning R games were replayed with the same full-state tracer, selected
by nearest land100 and game length for the three recurring cohorts:

| Loss cohort | Comparable win | land100 | Turns | First contact | Observable difference |
|---|---:|---:|---:|---:|---|
| EARLY_STALL | 22071 seat 1 | 3 | 1060 | 238 | Still early-stalled, but 10 recovery actions preceded land 44 at turn 200 and eventual enemy-general capture; this is the single C-loss to R-win flip. |
| DEFENSE_UNDERCOMMITTED | 22059 seat 1 | 45 | 676 | 102 | No qualifying threat to our general was observed; the candidate reached and captured the enemy general instead. |
| INTERCEPT_AVAILABLE_NOT_USED | 22080 seat 1 | 41 | 393 | 73 | No qualifying threat to our general was observed; the candidate reached and captured the enemy general instead. |

These controls establish direction more narrowly than aggregate defense-action
correlation: the two healthy comparable wins avoided the terminal defensive
state by winning the general race, while the loss traces entered a visible
last-30-turn threat state. They do **not** prove that globally increasing
"defense" would help.

The highest-value *testable next hypothesis* is
`INTERCEPT_AVAILABLE_NOT_USED` (10 independent losses): when a qualifying
visible general threat exists and an adjacent friendly move can defeat that
threat, prefer the winning local interceptor. This is deterministic, local,
representable with Agent-level board tests, and requires no scheduler redesign.
It therefore meets the stated eligibility gates for a future iteration, but is
only a recommendation here; no gameplay was changed. The broader
`DEFENSE_UNDERCOMMITTED` class (14) has no single proven local correction yet
and does not independently justify defense retuning.

### Protected ranges

`22100..22119` and `22150..22199` remain reserved for later fresh validation. No seed in `30000..30499` was used.

## V3.5 evidence-driven local-response iteration (2026-08-16)

### Revisions

- Expected starting revision: `d62f97bd26dcb3be574da526b6412dd06a69ec8d` (verified before editing).
- Recovery revert: `29b6052` (`v35: remove unproven stall recovery`).
- Winning local intercept: `8d188d5`.
- Staged local threat response: `b1d36af`.
- Catastrophic early-stall escape: `4f0fac7`.
- Exact V3.4 reference: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.
- Selected gameplay candidate: `4f0fac7`.

The recovery revert leaves `main.cpp` and `core.hpp` byte-equivalent to the
mandatory live-cost revision `ad9515c9` before the three new gameplay layers.
The intercept is a tier-0, exact-combat, adjacent capture of a qualified visible
general threat, with terminal enemy-general capture retaining higher utility.
The defense layer retains one ephemeral primary threat, prefers an exact kill,
then a conservative credible race, then a minimum sufficient local path block,
and only then short-ETA general reinforcement. The escape layer requires a
20-observation low-land/high-PASS stagnation window and is capped at ten actions,
eight land, threat/war preemption, and a 30-turn cooldown.

### Deterministic evidence

The fast suite passes 20 core checks plus Agent-level scenarios covering exact
winning intercept selection, insufficient-interceptor rejection, terminal-win
priority, incoming-stack local blocking and plan release, remote static contact,
and sustained-stall activation. This provides mechanism-level evidence only;
it is not match-level causal evidence.

### Used-seed causal diagnostics (`22050..22099`)

No score is claimed. The full diagnostic replay could not be completed in this
execution window. Consequently target-loss conversions, unrelated regressions,
and per-layer match points remain **unmeasured**. The layers remain separately
revertible commits so this required selection can be completed without retuning.

### Fresh Phase 1 (`22100..22119`)

No W/D/L or score is claimed. The first harness attempt correctly produced 40
infrastructure errors because `jax` and then the repository import path were
absent. After installing `jax` and setting `PYTHONPATH=.`, games ran correctly
but required roughly 40 seconds each in this container; the run was interrupted
after approximately two games rather than publishing an incomplete 40-game
result. Therefore the Phase-1 health/score gate is **not established**.

### Fresh Phase 2 (`22150..22199`) and loss classes

Not run, because Phase 1 did not complete. The protected `30000..30499` range
was not touched. New EARLY_STALL, INTERCEPT_AVAILABLE_NOT_USED,
DEFENSE_UNDERCOMMITTED, and other counts are unmeasured.

### Exact remaining risks

- The visible-stack identity heuristic is observation-based; crossing stacks can
  still make direction evidence ambiguous.
- Race selection deliberately requires an existing ATTACK packet and conservative
  army/ETA margin, so it can miss a real race rather than invent one.
- Local blocking uses current shortest-path geometry and exact current combat but
  cannot model an unseen supporting stack.
- Stall thresholds have deterministic safety tests but have not yet been checked
  against all 11 historical traces or healthy controls.
- Match-level value and regression counts are pending; do not treat this candidate
  as benchmark-selected until the used-seed causal replay and fresh gates finish.

## V3.5 fresh 221xx generalization validation

### Immutable experiment identity

- Selected gameplay commit: `4f0fac768a8fc4479d45347a3ecbdbfedd6aef05`.
- Validation starting commit: `cf51ae7be3194d48266557d8d589ac72efa6c58c`.
- Exact V3.4 baseline: `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.
- Workflow/report commit: the commit containing this section; the workflow also
  writes its full checked-out SHA to `benchmark/source-identity.txt`.
- Gameplay blobs at the validation start:
  - `main.cpp`: `42537039beac08f4ddb0113f7b53fa21997e4ec1`
  - `core.hpp`: `8c3a96028499e429c4a0b23c89d43fd95c67ef33`
  - `build.sh`: `8337d45f494bb04e385138f215a6ba55ef4d6d60`
  - `run.sh`: `fe8fa0e5a53678a06541833af361bf97f8d20bf0`

The validation-only diff from `cf51ae7` contains no change to any of those four
files. The three gameplay layers (`8d188d5`, `b1d36af`, and `4f0fac7`) remain
untouched and combined.

### Evidence separation and fresh protocol

The `22000..22019` result (**21 W / 5 D / 14 L, 58.75%**) and the
`22050..22099` result (**53 W / 18 D / 29 L, 62.0%**) are USED diagnostic
evidence only. They are not pooled with this experiment.

The workflow runs fresh Phase 1 only on `22100..22119` (40 paired-seat games),
requires zero errors, zero illegal actions, and score at least 54%, and only
then runs fresh Phase 2 on `22150..22199` (100 paired-seat games). The artifact
is always uploaded as `v35-fresh-221xx-validation`, including per-game audits,
stderr telemetry, summaries, seed/seat metadata, source identity, and Phase-2
full-state traces/loss forensics when the gate passes. No seed in
`30000..30499` is used.

### Results

Results pending execution of the validation workflow. No local partial run is
reported as a fresh measurement.

| Evidence | Phase 1 | Phase 2 | Health |
|---|---:|---:|---|
| Old fresh pre-fix | 56.25% | 56.0% | Phase 2 had 3 illegal actions |
| Recovery candidate | 56.25% | 54.0% | clean |
| New candidate USED 220xx | 58.75% | 62.0% | clean; diagnostic only |
| New candidate FRESH 221xx | pending | gated/pending | pending |

Phase results, seat split, paired CI, timing, land/PASS, threat, escape, castle,
defense telemetry, and fresh Phase-2 loss-class counts will be copied verbatim
from the uploaded JSON artifact after the workflow completes. Gameplay will not
be changed in response to the result.
