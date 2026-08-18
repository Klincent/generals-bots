# Current Codex task: repair and validate e50123 picker

## Goal

Fix the picker implementation properly. A runtime failure is not an acceptable final outcome for this task.

Reference champion:

`e50123cee7d924f0d643acd372a5300971f93917`

Broken isolated picker commit:

`c919246db8d6140638f1000a02bd9bbae8686f1b`

The picker-only screen attempted 60 games and all 60 failed because the candidate process closed stdout on the first request. Unit tests passed, so the existing tests are insufficient. Your task is to reproduce the real protocol failure, identify the exact root cause, fix it, add an integration regression test that would have caught it, and then evaluate/tune the picker competitively against exact e50123.

Do not work on anti-cycle or 3x3 exploration in this task.

## Strong debugging lead — verify, do not blindly assume

Compare the picker commit's `Agent::init()` line-by-line against exact e50123.

The picker diff removed the champion initialization of `owned_castle_history_`:

```cpp
owned_castle_history_.assign(n_,0);
for(int x=0;x<n_;++x)
  if(o.owner[x]==1&&o.type[x]==3)
    owned_castle_history_[x]=1;
```

but `act()` still indexes `owned_castle_history_[x]` and castle-recapture logic still reads it. This is a strong candidate for the first-observation crash. Prove the failure with sanitizer/debug instrumentation and verify whether this is the complete root cause. Also audit all other state initialization changed by the picker diff so no champion state was accidentally dropped.

## Required debugging procedure

1. Reproduce the failure from the broken picker commit with the real competition protocol, not only a unit test. Start with seed `31000`, both seats, using the same `competition/matchup.py` / `paired_benchmark.py` path used by the screen.
2. Build a debug binary with at least AddressSanitizer + UndefinedBehaviorSanitizer (`-fsanitize=address,undefined -fno-omit-frame-pointer -g`) and capture the first concrete failing stack trace / invalid access.
3. Compare the entire picker diff against exact e50123, especially `init()`, packet state, castle recapture state, observation/reconcile state, and any vector indexed by map cell.
4. Fix the root cause in coherent C++ source. Do not paper over the crash with bounds checks that silently disable champion behavior.
5. Add a regression/integration test that launches the real agent process or exercises the exact stdin/stdout protocol through at least the first complete observation and verifies that it returns a valid action. The test must fail on `c919246...` and pass on the fixed candidate.
6. Run the full existing unit/recovery/picker tests and release build.
7. Run a protocol smoke test on at least 10 seeds x both seats. Requirement: 0 crashes, 0 protocol errors, 0 illegal actions.

Do not proceed to competitive conclusions until runtime correctness is proven.

## Preserve champion behavior

The corrected candidate must remain a picker-only variant directly comparable to exact e50123.

Non-negotiable:

- preserve C1/C2 planning exactly as champion: sites computed once during initialization / turn 0;
- preserve `owned_castle_history_` initialization and castle recapture behavior;
- preserve champion castle funding/production logic;
- preserve champion threat/defense behavior;
- preserve champion anti-cycle semantics exactly as-is for this task;
- preserve champion exploration/search behavior exactly as-is for this task;
- do not steal the general stack, castle-funding/defense stacks, or live attack packets for picker work;
- do not introduce a parallel global scheduler.

The final branch should ideally have a small, reviewable diff against exact e50123: picker implementation + picker tests + protocol regression test, and nothing unrelated.

## Picker behavior to retain / improve

The picker exists to recover economically worthwhile stranded/rear/edge surplus army and deliver that mass toward a useful sink (strategic center, active front, confirmed enemy general / attack backbone).

Required properties:

- route must be owned/passable/safe enough before start;
- source must have genuine surplus after reserve/protection rules;
- picker must not use the general solely as a picker source;
- picker must not drain planned/current castle resources or a castle that needs defense;
- active attack packets are protected;
- picker can be pre-empted by true tactical emergencies and then resume when still valid;
- avoid repeated start/abort thrashing;
- require positive economic value: delivered useful mass must justify move cost;
- telemetry must include starts, completions, moves, delivered units, abort reasons, blocked ticks, source-guard rejects, planned mass/moves, and effective delivered-units-per-picker-move.

## Competitive benchmark and tuning loop

Once runtime correctness is established, benchmark against exact `e50123cee7d924f0d643acd372a5300971f93917` with identical RNG seeds and both seats.

### Screen

Run 30 seeds x both seats = 60 games on:

`31000..31029`

Report W/D/L, score, bootstrap/paired 95% CI if tooling supports it, errors, illegal actions, latency, and picker telemetry.

Also compare candidate vs champion on identical seeds for:

- land T50/T100/T150/T250;
- C1/C2 build status and timing;
- war/enemy/attack actions;
- passes;
- picker starts/completions/moves/delivered/aborts;
- representative losses.

### Do not stop at the first non-crashing mediocre result

This task is specifically to make the picker work, not merely to classify the broken version.

If runtime is correct but the first screen score is below 0.48, inspect losses and picker economics and make up to **three small, evidence-based tuning iterations**. Typical knobs may include start threshold, minimum efficiency, protected-source rules, sink selection, cooldown/resume logic, and pre-emption policy. Change one coherent cause at a time and rerun the same 60-game screen so the effect is attributable.

Do not compensate for a weak picker by modifying castle strategy, exploration, anti-cycle, or general attack architecture.

### Confirmation

When a fixed/tuned picker reaches all of the following:

- score >= 0.48 on the 60-game screen;
- 0 runtime/protocol errors;
- 0 illegal actions;
- no material collapse in land/castle/war telemetry;
- picker telemetry demonstrates useful delivered mass rather than move churn;

run an independent 60 seeds x both seats = 120-game confirmation on:

`32000..32059`

A point estimate above 0.50 is encouraging but not sufficient by itself; report uncertainty and loss diagnosis.

## Branching / commits

Use a new branch such as:

`codex/e50123-picker-fix`

You may debug starting from the broken picker commit, but the final candidate must be easy to compare to exact e50123 and must not carry unrelated later V3.6 changes.

Prefer a clean final commit series such as:

1. reproduce + protocol regression test,
2. root-cause runtime fix,
3. minimal picker tuning if justified.

Do not merge to master.

## Deliverables

At completion:

1. append a new section to `docs/codex/RESULTS.md` (do not erase the previous ablation results);
2. state the exact crash root cause and sanitizer evidence;
3. identify any additional initialization/state regressions found in the broken picker diff;
4. provide branch + final commit SHA;
5. list exact files changed;
6. provide full unit/build/protocol-smoke results;
7. provide every picker screen iteration W/D/L/score and what changed between iterations;
8. provide confirmation benchmark if the gate is met;
9. provide key land/castle/war/picker telemetry and representative-loss diagnosis;
10. recommend either `READY TO COMBINE/SUBMIT`, `FIXED BUT NEEDS MORE TUNING`, or `PICKER IDEA COMPETITIVELY REJECTED`.

Important: `PICKER IDEA COMPETITIVELY REJECTED` is only valid after the runtime bug has been fixed and a valid non-crashing competitive benchmark has actually been run. A crash is a bug to debug, not a competitive conclusion.
