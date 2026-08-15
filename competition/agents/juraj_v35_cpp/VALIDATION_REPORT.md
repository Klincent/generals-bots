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
