# V3.5 Validation Report

## Revision

- Branch: `v35-heuristic-rebuild`
- Starting revision: `a81eb35177c5db6fb07cb70fc14791068c9647d8`
- Report/source revision: see the commit containing this report (`git rev-parse HEAD`; a Git commit cannot embed its own SHA without changing it).
- Exact reference: `juraj-v3.4` at `2ed9e8bbcf76b36c5276013afc356118fccc8b6e`.

## Production data-flow audit and implementation

This iteration fixes the most serious audit defect: logistics packets are now owned by `Agent`, reconciled after real observations, retain IDs, roles, objectives, front IDs, assignment event/version, army, idle/revisit counters, and bounded paths. Actual moves update these packets; disappeared flows are retired. Route cycle rejection is therefore applied to runtime history rather than a one-turn temporary object. Objective and reversal counters report real runtime events.

A persistent `FrontManager` clusters contacts within graph distance four, retains anchors through fog, and transitions ACTIVE to STALE and CLOSED with hysteresis. Front add/close changes the strategic event version, and logistics assignments retain a front ID.

The runtime now confirms a legally visible enemy general and pins belief mass to it. Confirmed information cannot subsequently be eliminated or overwritten by flow back-projection. Zero-mass unconfirmed belief recovers from its valid initial support rather than selecting cell zero accidentally.

Opponent evidence now uses retained land/army history (5/10/20/50-turn slopes), a real visible size median, opponent-only castle observations, active front count, and visible concentration. Missing visibility uses low evidence rather than fabricating a packet average. Existing probabilistic archetype adaptation now affects expansion/search/war/defense allocation and candidate availability, although the reaction fingerprint remains incomplete.

Strategic objectives use a separate tactical next-hop filter. It rejects visible losing captures and cells immediately counterattacked by a stronger visible enemy. Rear evacuation and war mobilization are persistent FULL-1 assignments. Resource categories cap generated expansion/search/war assignments rather than merely being printed.

Castle C1/C2 state is sequential: C2 does not fund/build until C1 is observed BUILT, and a built castle has zero remaining funding. JIT lifecycle states are updated in runtime. Full unsafe-site replanning is still partial.

## Tests

- `competition/agents/juraj_v35_cpp/build.sh`: passed.
- `competition/agents/juraj_v35_cpp/test.sh`: passed (20 core checks plus real-Agent scenarios across observation boundaries).
- Agent scenarios cover persistent rear movement, packet reconciliation, confirmed enemy-general targeting state, production emergency behavior, and front hysteresis through fog.

## Benchmark / Actions

- GitHub Actions workflow: `.github/workflows/v35-heuristic.yml` builds both binaries once, then launches fresh processes for paired games.
- Actions run ID: pending for this pushed revision.
- 40-game Phase 1 (`21000..21019`): pending GitHub Actions; W/D/L, score, seat split, paired CI, timing, illegal actions and errors are therefore not yet claimed.
- 100-game Phase 2 (`21100..21149`): gated on Phase 1 score >=40%; pending.
- No seed in the forbidden `30000..30499` range was used.

## Remaining limitations / risks

This is an honest incremental production repair, not a claim that every requested mechanism is complete. Reaction latency/overreaction tracking, deterministic unsafe castle replanning, full merge/split identity, detailed +10/+25/+50 front snapshots, complete per-archetype Agent action scenario coverage, and broad V3.4 tactical parity remain partial. The current one-ply safety rule is deliberately conservative and does not yet reproduce all V3.4 combat simulation. Representative win/loss analysis and qualitative benchmark metrics must be filled from the new Actions artifacts before submission review.

## Next action

Inspect the Phase 1 Actions artifact. If score is below 40%, classify at least five trace losses and repair the dominant tactical/expansion failure before using a fresh non-heldout range. If the gate passes, inspect Phase 2 and update this report with exact results and representative games.
