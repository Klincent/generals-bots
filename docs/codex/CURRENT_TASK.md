# Current Codex task: selective economy-safe picker v3

## Context

Reference champion:

`e50123cee7d924f0d643acd372a5300971f93917`

Useful implementation history:

- runtime-correct picker base: `codex/e50123-picker-fix`
- non-modal picker experiment: `b1edc4015f5e0a9f8c4f306e458e0d64d849d734`
- short-handoff experiment: `96063b069b6c642f6ebf4ba637eedaf3ee8845b2`

The 60-game screen for the short-handoff picker looked promising at 29/6/25 = 0.5333, but an untouched 120-game confirmation on seeds 32000..32059 failed badly:

- 37 W / 18 D / 65 L
- score 0.3833
- paired 95% CI [0.3125, 0.4542]
- 0 errors / 0 illegal actions

The confirmation forensics are important:

- some wins clearly showed a real picker benefit: smaller land/economy but much larger concentrated stacks that converted into decisive general pressure;
- in aggregate the picker still damaged economy too often;
- candidate had about 28 fewer expansion actions/game and a large T250 land deficit;
- most picker moves occurred in nominally low-opportunity/idle slots, so simple scheduler competition alone is not enough;
- the core failure is that picker activation is too unconditional across game states. It is useful in some states and harmful in others.

Do not resurrect the old modal picker and do not simply retune mass threshold again.

## Primary objective

Build a **selective picker that activates only when the current game state can afford consolidation and the expected concentration benefit is worth the economic risk**.

The goal is not maximum delivered mass. The goal is a picker that improves paired win rate versus exact e50123 on independent seeds.

The final candidate must remain picker-only relative to exact e50123. Do not modify anti-cycle, 3x3 exploration, castle policy, threat defense or attack architecture.

## Development data and holdout discipline

The following seed pools are already spent and may be used for diagnosis/tuning:

- `31000..31029`
- `32000..32059`

Do not call either pool an independent confirmation again.

Use a fresh holdout for final validation:

- `33000..33059`, both seats = 120 games

If the result is promising but uncertain, use another untouched holdout:

- `34000..34059`, both seats = 120 games

Do not tune on 33000/34000 after seeing their outcomes.

## Phase 1 — data-driven picker-start forensics

Before changing runtime policy, deterministically replay the spent development pools and instrument every potential/actual picker start with a compact state snapshot.

At minimum collect:

- turn
- my_land / opp_land / land delta
- recent land growth slope over roughly 25 and 50 turns
- my_army / opp_army / army delta
- largest owned stack and top-3 owned stack mass/share if practical
- scattered owned mass in small stacks if practical
- current edge/rear surplus mass proposed for picker
- proposed picker moves and estimated delivered mass
- reachable neutral expansion opportunities / count of immediately useful neutral candidates
- distance to nearest useful neutral expansion if practical
- enemy seen / meaningful contact / active fronts
- enemy general confirmed
- production state and turns to next production tick
- C1/C2 urgency/build status
- whether an attack/front packet already exists
- whether the game eventually won/lost
- local 50-turn change in land/army after picker start where available

Use the spent 31000/32000 pools to identify simple interpretable conditions separating helpful picker starts from harmful ones. Do not train a large black-box model. Small offline scripts/grid searches are fine for analysis, but runtime policy must remain simple deterministic C++.

Important hypotheses to test, not blindly assume:

1. Picker is safer after early expansion is largely established.
2. Picker is safer when recent land growth is healthy rather than stalled.
3. Picker is safer when we are not materially behind the opponent in land/economy.
4. Picker is most useful when edge surplus is large but concentration is poor (no existing decisive stack).
5. Picker should stay off when many cheap neutral expansion opportunities remain.
6. Picker may be useful after meaningful contact when it can feed a real attack/front sink, but not when it merely carries mass toward the general.

Report which of these are actually supported by the spent replay data.

## Phase 2 — implement small selective variants

Work on branch:

`codex/e50123-picker-selective-v3`

Use the non-modal picker architecture as the implementation starting point, but exact e50123 remains the benchmark reference.

Create at most three small, attributable runtime policies. Suggested structure:

### Variant A — economy-health gate

Picker may start only when an evidence-derived economy/expansion health condition is satisfied.

Examples of possible signals:

- minimum turn / expansion maturity
- recent land slope not stalled
- not materially behind opponent land
- low count of useful neutral expansion candidates

Choose thresholds from replay evidence rather than arbitrary guessing.

### Variant B — concentration-need gate

Build on A only if justified. Require that consolidation is actually needed:

- substantial edge/rear surplus exists
- no already-dominant attack stack / top-3 concentration is below an evidence-derived threshold
- projected delivered mass per dedicated move remains worthwhile

Do not move army merely because it exists on an edge.

### Variant C — attack-fed / hybrid gate

Only if justified by forensics, allow picker preferentially when it can hand off into a meaningful front/attack backbone or when the economy-health + concentration-need conditions both hold.

Prefer a useful front/interior handoff over the general when appropriate.

Do not make unrelated strategy changes between variants.

## Piggyback and dedicated move policy

Keep the picker non-modal and resumable.

- HARD actions always win.
- Expansion starvation protection remains champion-equivalent.
- Meaningful war/offense yields priority.
- Pause is not abort.
- Prefer piggyback progress when an unchanged champion logistics/war move naturally advances the collector.
- Dedicated picker moves are allowed only after the selective activation gate has passed.
- Track dedicated vs piggyback moves separately.

A picker that starts 1-2 times/game and wins more is better than one that delivers 400 units/game and loses.

## Development benchmark protocol

For each A/B/C candidate:

1. full unit/recovery/picker/protocol tests and release build;
2. 60-game paired screen on `31000..31029`;
3. 120-game paired development check on `32000..32059` if the 60-game result is not clearly bad;
4. compare the candidate's behavior against exact e50123 and against the known failed short-handoff picker.

Because 31000/32000 are development data now, use them for ranking/tuning only, not final claims.

Required telemetry:

- W/D/L and score
- errors/illegal actions
- land T50/T100/T150/T250
- expansion actions
- war/offense/search actions
- C1/C2 frequency/timing
- picker eligible opportunities
- picker starts/completions
- dedicated picker moves
- piggyback picker moves
- delivered mass
- delivered mass per dedicated move
- gate rejects by reason (economy, expansion opportunity, concentration already sufficient, behind/stalled, no useful sink, etc.)
- per-start turn distribution

## Final holdout gate

Pick exactly one best selective candidate before looking at the final holdout.

Freeze its source and commit SHA.

Then run:

- seeds `33000..33059`
- both seats
- 120 games
- exact e50123 baseline
- no tuning, no early stopping, no source edits

Interpretation:

- score >= 0.52 with 0 errors/illegal actions: strong candidate; run second holdout 34000..34059 for confirmation
- score 0.50..0.52: promising; run 34000..34059 before any submission decision
- score 0.48..0.50: inconclusive; do not submit yet
- score < 0.48: reject that selective policy

If a second holdout is run, require the combined evidence from 33000+34000 to be at least non-regressing and preferably >0.50 before recommending submission.

## Loss and win forensics

Do not inspect only losses. For the final candidate inspect at least five wins and five losses.

Specifically answer:

- when picker helped, what state made consolidation valuable?
- when picker hurt, why did the gate permit it?
- did winning picker games show larger decisive stacks / earlier general pressure / better war conversion?
- did losing games still show economy damage, or are losses unrelated to picker activity?

If a loss occurs with zero picker starts, do not attribute it to picker.

## Deliverables

Append results to `docs/codex/RESULTS.md`.

At completion provide:

- branch + SHA for each tested variant
- exact selective gate rules and why the data supports them
- 31000/32000 development W/D/L for each variant
- telemetry and gate rejection counts
- frozen final candidate SHA
- untouched 33000 holdout result
- untouched 34000 holdout result if triggered
- 95% paired/bootstrap intervals
- 5-win / 5-loss forensic summary
- explicit recommendation: REJECT / PROMISING BUT UNCONFIRMED / CONFIRMED SUBMISSION CANDIDATE

Do not create a leaderboard submission until a frozen candidate survives fresh holdout testing.