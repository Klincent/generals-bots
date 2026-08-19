# Current Codex task: finish selective picker v3 validation

## Situation

Reference champion: `e50123cee7d924f0d643acd372a5300971f93917`.

Codex created `codex/e50123-picker-selective-v3`, but validation is incomplete: only a 1-map / 2-game smoke test was run. This is not competitive evidence.

There is also a provenance problem: the pushed branch does not descend cleanly from exact e50123. The next work must make the final experimental candidate easy to audit against the exact champion.

## Objective

Do not redesign the picker again yet. First finish a scientifically valid benchmark of the existing selective-gate prototype.

## Required clean branch

Create a fresh branch directly from exact champion:

`codex/e50123-picker-selective-v3-clean`

Start at exactly:

`e50123cee7d924f0d643acd372a5300971f93917`

Transplant only the selective-picker implementation and its required tests/telemetry from `codex/e50123-picker-selective-v3`. Do not copy unrelated workflows, docs history, analysis artifacts, later V3.6 changes, anti-cycle changes, 3x3 changes, or other strategy changes.

Verify with git that the merge-base with e50123 is e50123 itself.

## Preserve champion invariants

Keep exact champion behavior outside picker:

- castle planning/funding/recapture
- threat/general defense
- expansion scheduler/economics
- search behavior
- attack/war architecture
- anti-cycle behavior

Keep the previously fixed `owned_castle_history_` initialization and real stdin/stdout protocol regression test.

## Existing selective gate

Preserve the current prototype gate for the first benchmark. Do not tune it before obtaining a full result. Its current rules include roughly:

- expansion maturity: turn >=150 or >=35% map ownership
- no worse than ~20% land deficit
- recent growth requirement, waived at high map ownership
- <=3 immediately capturable neutral frontiers
- top-three stack share <55%
- no existing stack already as large as the proposed delivery

The exact source on the pushed v3 branch is the authority; document the exact final rule after transplant.

## Validation sequence

1. Full unit/recovery/picker/protocol tests.
2. Release build.
3. Protocol smoke: 10 seeds x both seats, 0 errors/illegal required.
4. Development screen on spent seeds `31000..31029`, both seats = 60 games versus exact e50123.
5. If score >=0.48 and runtime is clean, development confirmation on `32000..32059`, both seats = 120 games.
6. If both development pools are not clearly bad, freeze the exact candidate SHA before any fresh holdout.
7. Run untouched holdout `33000..33059`, both seats = 120 games. No tuning, source changes, early stopping, or threshold changes after seeing holdout results.
8. Only if 33000 score is >=0.50, run second untouched holdout `34000..34059`, both seats = 120 games.

Do not stop after a smoke test. A smoke test is not a competitive result.

## Metrics

For every full benchmark report:

- W/D/L, score, paired/bootstrap 95% CI
- errors and illegal actions
- latency
- land T50/T100/T150/T250
- expansion, war/offense, search actions
- C1/C2 frequency/timing
- picker eligible opportunities
- picker starts/completions
- dedicated picker moves and piggyback moves
- delivered mass and delivered mass/dedicated move
- start-turn distribution
- gate rejection counts by reason

For the frozen candidate inspect at least five wins and five losses. Do not blame picker in games with zero picker starts.

## Decision

- fresh holdout score >=0.52 and healthy telemetry: strong candidate; run second holdout
- 0.50..0.52: promising; run second holdout
- 0.48..0.50: inconclusive, do not submit
- <0.48: reject

A leaderboard submission is allowed only if a frozen candidate survives fresh holdout validation.

## Deliverables

Update `docs/codex/RESULTS.md` with:

- clean branch and SHA
- proof branch descends directly from e50123
- exact files transplanted
- exact selective gate
- test/build/smoke results
- 31000 and 32000 development results
- frozen candidate SHA
- 33000 holdout result
- 34000 result if run
- final classification: REJECT / PROMISING BUT UNCONFIRMED / CONFIRMED SUBMISSION CANDIDATE

Do not return merely because time-consuming benchmarks remain. The task is incomplete until the required benchmark sequence is either completed or a concrete external execution blocker is documented.