# Juraj C++ agent: non-negotiable invariants

These instructions apply to all files under `competition/agents/juraj_v35_cpp/`.

## Reference champion

The current strategic reference is the exact commit:

`e50123cee7d924f0d643acd372a5300971f93917`

Do not use later V3.6 implementations as the architectural baseline unless the task explicitly says so. When a task says to start from the champion, create the experimental variant directly from this exact commit and preserve unrelated champion behavior.

## Castle rules

- Future castle positions C1 and C2 are computed once during initialisation / turn 0 from the initial map. Do not relocate or re-plan them later because the game state changed.
- Preserve the champion's castle funding and production logic unless the task explicitly targets it.
- Preserve castle recapture: a castle that was ours and is captured by the opponent remains a high-priority recapture objective when a safe recapture is available.
- Do not let castle funding permanently starve expansion, exploration, picker logistics or war unless the existing deadline logic genuinely requires it.

## Exact anti-cycle semantics

Anti-cycle state is local to the moving packet/chunk, not global across unrelated armies.

Remember the last four directed transitions of that packet. Block a candidate directed edge only when that exact `(from,to)` edge already occurs inside that four-transition window.

Required examples:

- `A -> B -> A` is allowed.
- `A -> B -> A -> B`: the final `A -> B` is blocked.
- `A -> B -> C -> B` is allowed.
- after `A -> B -> C -> B`, another `B -> C` is blocked.
- `A -> B -> C -> D -> A` is allowed.
- after that sequence, `A -> B` is blocked while it is still within the last-four-edge window.
- once an edge expires from the four-edge window, it is allowed again.
- `GENERAL_EMERGENCY` and `TERMINAL_CAPTURE` bypass the guard.

Do not replace this with a recent-cell taboo, a blanket immediate-reverse ban, or a global action-history ban.

## 3x3 exploration / expansion

Conceptually divide the map into a 3x3 sector grid.

- The general starts in one sector; the bot should make meaningful progress toward exploring the other eight sectors when they are reachable.
- Exploration is a coverage objective, not permission to sacrifice the champion's early land growth or military strength.
- Do not drain the general or the main attack stack merely to satisfy sector coverage.
- Do not force exploration every turn. Preserve expansion/war economics and use bounded/persistent probes.
- Stop or de-prioritise search when enemy information makes further blind exploration strategically inferior.
- Track and report sector touch/sweep telemetry so losses can be diagnosed.

## Picker

The picker is logistics: recover stranded/rear/edge army and deliver useful mass toward the strategic centre, active front or attack backbone.

- Never steal the general stack solely to run picker logic.
- Do not drain a castle under construction, a castle that must be defended, or a live attack packet.
- A picker route must have a realistic completion path before it starts.
- A temporarily pre-empted picker should be resumable; do not repeatedly restart/abort it without cause.
- Picker should justify its move cost economically. Report starts, completions, moves, delivered units and aborts.

## Runtime failures are bugs, not strategic verdicts

If a feature branch crashes, closes stdout, violates the agent protocol, or produces invalid/illegal actions, do not classify the feature as competitively rejected yet.

- Reproduce the exact failure with the real competition protocol.
- Use ASan/UBSan or an equivalent debug build to identify the concrete invalid access / undefined behavior.
- Compare initialization and persistent state against the exact champion so feature work does not accidentally delete unrelated state.
- Add an integration regression test that fails before the fix and passes after it.
- Only make a competitive keep/reject decision after the candidate completes a valid non-crashing benchmark.

A unit test pass does not override a real protocol crash.

## Attack and global strategy

A requested local feature must not weaken the champion's attack pipeline. Check that the bot still transitions from land growth / search into gathering and decisive war activity.

When investigating a regression, inspect at least:

- land at T50/T100/T150/T250 (and later if useful),
- C1/C2 build status and timing,
- sector coverage,
- picker starts/completions/delivered units,
- enemy/war/attack moves,
- passes, illegal actions and runtime errors.

## Tests

Keep existing tests unless they contradict the explicit semantics above. If an old test encodes obsolete cycle behavior (for example banning `A-B-A`), update that test rather than weakening the required semantics.

Run:

```bash
bash competition/agents/juraj_v35_cpp/test.sh
bash competition/agents/juraj_v35_cpp/build.sh
```

Then run the paired benchmark protocol from `docs/codex/CURRENT_TASK.md` before declaring a strategic change successful.
