# V4.1 post-training task for Codex

## Context

The expensive rollout collection is complete. Do **not** regenerate the 5000-game training campaign.

Final GitHub Actions training run:
- repository: `Klincent/generals-bots`
- branch: `experiment/v4.1-github-training`
- workflow run id: `31595349356`
- final training artifact: `v41-final-training-state`
- artifact id: `9164275598`
- final handoff artifact: `v41-final-handoff`
- artifact id: `9164274843`

Final checkpoint:
- games: `5000`
- states: `47736`
- raw_rollouts: `1452956`
- usable_pairs: `1094917`
- data_bytes: `22648318`
- feature_schema: `2`
- pack_version: `2`
- candidates/state: `8`
- rollouts/candidate: `4`
- horizon: `50`
- current fitted policy bytes: `3145792`
- current nonzero weights: `242`
- runtime main SHA256: `a9302e07040f083547c2372aecff141fbaa5e613daabf75d29dfa158c5fb2012`

The current automatic `policy.bin` is **not accepted as a production-quality model** merely because the training gate passed. The current fitter stores `int16` weights and the previous 3480-game candidate already showed hard saturation at INT16_MIN/INT16_MAX. Therefore the post-training phase must audit and replace the fitter/model representation before benchmarking.

The raw expensive product is `rollouts.jsonl.gz` inside the final training artifact. Codex does not need to fetch that artifact during development. Implement the code and GitHub Actions workflow so that Actions later downloads artifact `9164275598` / run `31595349356` and performs the full fit/validation there.

## Existing code to inspect first

Read and understand at minimum:
- `competition/training/v4/rollout_train.py`
- `competition/training/v4/run_github_chunk.py`
- `competition/training/v4/github_finalize.py`
- `competition/training/v4/prepare_v41_runtime.py`
- `competition/training/v4/test_rollout_train.py`
- `competition/training/v4/test_github_pipeline.py`
- `competition/matchup.py`
- runtime V4.1 code reconstructed by `prepare_v41_runtime.py`
- current V4 policy/tactics loader and scoring code in reconstructed runtime

Preserve all V3.4 hard-safety behavior. Learned policy/tactics may rank ambiguous ordinary actions but must not bypass hard safety logic.

## Goal

Produce a robust V4.1 candidate, then benchmark it against the exact corrected V3.4 baseline using held-out competition maps.

The deliverables are:
1. a new audited `policy.bin` produced from the existing 1,094,917 pair comparisons;
2. a real `tactics.bin` (if exact tactical keys can be produced honestly); otherwise implement a targeted tactical miner and workflow that creates one from actual `GeneralsEnv(mode="competition")` states;
3. runtime support for the final policy/tactics formats;
4. deterministic ablation switches;
5. a GitHub Actions post-training workflow that performs fitting, tactical mining if required, and held-out V3.4-vs-V4.1 validation;
6. machine-readable reports/artifacts sufficient to decide whether V4.1 should replace V3.4.

## Policy fitter requirements

The model remains a **sparse feature-hashed linear ranking policy**. This is not a neural network.

Training examples are pairwise candidate comparisons from the stored rollout records. For a pair `(A,B)` use the sparse feature difference `x_A - x_B` and learn the sign/order implied by the rollout outcome.

Replace the current uncontrolled integer accumulation with a proper regularized optimizer:
- train weights in `float32` or `float64`;
- use pairwise logistic loss or an equivalently justified pairwise ranking loss;
- add L2 regularization;
- split train/validation by **game seed**, never by individual pair, to avoid leakage between states from the same game;
- use deterministic seeds/configuration;
- do not let extreme rollout deltas (for example terminal-loss-derived ~25k deltas) create unbounded gradients/weights; use sign plus a bounded confidence/sample weight or another explicitly justified bounded transformation;
- report train and validation pairwise accuracy/loss and calibration-like ranking diagnostics;
- report weight distribution percentiles, max abs weight, support/coverage, intervention rate, and any hash collisions actually present in reachable schema-v2 features.

Preferred production representation: `float32` weights unless a smaller quantized representation is proven safe. `int32` is acceptable as an optional deterministic quantized representation. `int16` may be emitted only if quantization is derived from the fitted float model and clipping/saturation is effectively zero and tested. Do not simply change the accumulator type from int16 to int32 and call the problem solved.

Version the binary format so old pack/schema files are rejected safely. Missing/corrupt learned files must fall back to deterministic V3.4 behavior.

## Tactics requirements

Current 5000-game campaign primarily generated policy-ranking data, not a trustworthy new tactics database.

Inspect the existing runtime tactic key and loader. Determine whether an exact runtime `v4_tactic_key` can be reconstructed from the stored rollout record fields. If not, **do not fabricate tactics records from incomplete information**.

In that case implement a targeted tactical miner using the real `GeneralsEnv(mode="competition")`. Focus sampling on contact/threat/combat states where exact local tactical knowledge is useful. It must:
- generate only valid competition states/actions;
- evaluate alternatives with controlled/common-seed rollouts or exact short tactical resolution where appropriate;
- write sorted, deduplicated tactic records using the exact runtime key format;
- store value plus support/visits/confidence;
- have minimum-support filtering;
- produce diagnostics: number of unique records, visits distribution, collisions/duplicates, hit-rate estimate on held-out tactical states.

Keep this tactical campaign much smaller and more targeted than the completed 5000-game general rollout campaign.

## Runtime ablations

Implement deterministic switches so the same V4.1 runtime can run as:
- policy OFF, tactics OFF
- policy ON, tactics OFF
- policy OFF, tactics ON
- policy ON, tactics ON

The OFF/OFF mode should be behaviorally equivalent to corrected V3.4 except for unavoidable wrapper/version plumbing; prove this with tests/benchmarks.

Log counters without polluting stdout protocol, e.g. via stderr or optional telemetry file:
- policy considered
- policy actually changed chosen action
- insufficient-support fallback
- small-margin fallback
- tactic lookup attempts/hits
- tactic action changes
- timing percentiles

## Validation harness

Build a non-GUI batch harness around the real competition engine/ruleset. Use the exact corrected V3.4 baseline and the V4.1 candidate.

Primary final benchmark:
- held-out seeds `30000..30499` (500 distinct maps)
- each seed played twice with seats swapped
- total `1000` games
- `GeneralsEnv(mode="competition")`
- fresh subprocesses per match or another implementation proven protocol-equivalent
- compile agents once per shard, not once per game
- record seed, seat assignment, winner/draw, turns, timing, castle counts and available learned-policy/tactics telemetry

Report:
- W / D / L for V4.1
- score `(W + 0.5*D)/N`
- P0 and P1 split
- paired-map results by seed
- paired bootstrap 95% CI over seeds (not naive independent-game binomial CI)
- runtime timing percentiles and maxima
- crashes/protocol errors/timeouts

Also run ablations, preferably at least several hundred paired games each:
A. V4.1 policy ON/tactics OFF vs V4.1 OFF/OFF
B. V4.1 tactics ON/policy OFF vs V4.1 OFF/OFF
C. full V4.1 vs exact V3.4

Do not claim success just because training gates are met. The final acceptance decision is based on held-out game performance and safety/timing.

Suggested interpretation for the 1000-game paired benchmark:
- below 50% score: reject
- 50-52%: no convincing edge
- 52-54%: marginal
- 54-55%: good
- >=55%: compelling
- >=57%: excellent
Use paired CI and diagnostics, not score alone.

## GitHub Actions implementation

Add a post-training workflow that can be triggered manually and that:
1. downloads `v41-final-training-state` from run `31595349356` using official `actions/download-artifact@v4` with `github-token`, `repository`, and `run-id`;
2. validates checkpoint config and data byte count before fitting;
3. runs the new policy audit/fitter against the full `rollouts.jsonl.gz`;
4. creates/validates `policy.bin`;
5. creates `tactics.bin` via exact extraction if possible, otherwise runs the targeted tactical miner;
6. reconstructs/builds exact corrected V3.4 and V4.1 runtimes;
7. runs unit/integration tests;
8. runs sharded held-out validation to stay within Actions job limits/timeouts;
9. aggregates results;
10. uploads final candidate files and reports as artifacts.

Do not depend on arbitrary outbound network access from Python. Use official GitHub Actions artifact actions for artifact transfer.

## Required output files

At minimum produce:
- `competition/training/v4/fit_policy_v41.py` (or well-named equivalent)
- tests for the fitter and binary format
- tactics builder/miner plus tests
- batch validation/aggregation scripts plus tests
- runtime changes/patches needed for new policy/tactics format and ablation flags
- `.github/workflows/v41-posttrain.yml` plus any reusable shard workflow(s)
- a short `competition/training/v4/POSTTRAIN_README.md`

The final GitHub artifact should contain at least:
- `main.cpp` for V4.1
- `policy.bin`
- `tactics.bin` if successfully produced
- build/run scripts suitable for candidate testing
- `policy-report.json`
- `tactics-report.json`
- `benchmark-summary.json`
- raw per-game benchmark CSV/JSONL
- manifest with SHA256 of all candidate files and exact source commit

## Safety / non-regression constraints

Do not weaken or redesign these locked V3.4 behaviors unless necessary for binary-format plumbing:
- hard rear evacuation / two-layer belt behavior
- castle timing/program C1/C2/C3
- FULL-FIRST SMART-FORK split policy
- anti-cycle logic
- hard threat/general defense behavior

Do not replace deterministic hard-safety decisions with learned ranker outputs.

## Before finishing

Run all feasible local tests. Summarize:
- files changed
- exact model/loss/regularization chosen and why
- policy binary format
- tactics generation method
- how to trigger the post-training workflow
- expected artifacts
- any remaining limitation that requires GitHub Actions compute rather than local Codex execution.
