# Current Codex task: isolate regressions from e50123 champion

## Goal

Start from the exact reference champion:

`e50123cee7d924f0d643acd372a5300971f93917`

The recent combined port of picker + 3x3 exploration + anti-cycle regressed badly versus this champion. Do not attempt another combined rewrite. First isolate each feature independently and determine which feature(s) can be added without destroying champion strength.

This task is forensic and experimental before it is integrative.

## Required experimental variants

Create three independent variants, each directly from the exact champion commit. Do not stack these variants on top of each other.

### Variant A — anti-cycle only

Add only the exact per-packet four-directed-edge anti-cycle semantics defined in `competition/agents/juraj_v35_cpp/AGENTS.md`.

Do not change picker, exploration, castle logic, scheduler shares, attack priorities or other strategy.

### Variant B — picker only

Add only a minimal, coherent picker implementation.

Requirements:

- gather stranded/rear/edge surplus army;
- preserve general, castle funding/defence and active attack stacks;
- start only when there is a realistic route and positive economic value;
- be resumable after higher-priority tactical work;
- expose telemetry: starts, completions, moves, units delivered, aborts.

Do not add 3x3 exploration or anti-cycle changes in this variant.

### Variant C — 3x3 exploration only

Add only 3x3 sector exploration/coverage.

Requirements:

- compute the 3x3 sector layout deterministically from the initial map;
- preserve the champion's initial expansion economics;
- make meaningful progress toward the other eight reachable sectors;
- use bounded/persistent probes rather than globally forcing search every turn;
- do not drain the general, castle funding stack or primary attack stack merely for coverage;
- expose telemetry for reachable/touched/swept sectors and probe moves.

Do not add picker or anti-cycle changes in this variant.

## Castle invariants for all variants

These are not experimental variables and must remain unchanged unless required to fix a direct integration bug:

- C1/C2 future castle sites are selected once during initialisation / turn 0.
- Preserve the champion's castle production/funding policy.
- Preserve recapture of our previously owned castles.
- No new sticky funding or global HARD-priority mechanism that starves the rest of the strategy.

## Benchmark protocol

Use exact `e50123cee7d924f0d643acd372a5300971f93917` as baseline.

For each of A/B/C:

1. run the complete unit/regression suite and build;
2. run a first paired screen of **30 seeds x both seats = 60 games** on seeds `31000..31029`;
3. if score is at least 0.48, there are no errors/illegal actions, and telemetry shows no severe strategic collapse, run an independent confirmation of **60 seeds x both seats = 120 games** on seeds `32000..32059`;
4. if score is clearly below 0.48 or land/war behaviour collapses, stop that variant and diagnose representative losses rather than tuning it blindly.

A variant is not considered safe merely because its point estimate is above 0.50. Report uncertainty / confidence interval when the benchmark tooling supports it.

## Required metrics

For every tested variant report:

- W / D / L and score;
- errors and illegal actions;
- runtime latency summary;
- land at T50, T100, T150 and T250;
- C1/C2 built/missing and build timing;
- war/enemy/attack activity;
- variant-specific telemetry (anti-cycle blocks, picker economics, or sector coverage).

Compare loss telemetry against the champion on identical seeds where possible.

## Integration gate

Do **not** combine features until the independent results are understood.

After A/B/C:

- identify which features are non-regressing or improving;
- explain why any regressing feature loses;
- only then test combinations of individually safe features;
- every combination must again be benchmarked against exact e50123 on identical seeds and both seats.

If none of A/B/C is safe, keep e50123 as champion and report that result instead of manufacturing a new submission.

## Implementation quality

- Read the current champion code before editing.
- Implement source changes coherently in C++, not as permanent brittle string-replacement patch scripts.
- Preserve unrelated champion behaviour.
- Add focused tests for the exact semantics of each variant.
- Do not merge to master.
- Work on feature branches/commits that make the three experiments easy to inspect independently.

## Deliverables

Update `docs/codex/RESULTS.md` with:

- branch and commit SHA for each variant;
- exact diff intent;
- test/build status;
- benchmark seed ranges and W/D/L/score;
- key telemetry and representative loss diagnosis;
- recommendation: reject / keep for combination / confirmed improvement.

At the end, provide a concise recommendation for the next competitive branch. Do not create or upload a leaderboard submission unless a tested candidate clearly justifies replacing e50123.
