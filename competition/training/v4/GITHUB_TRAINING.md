# V4.1 GitHub-hosted training handoff

Opening or synchronizing a pull request containing `.github/workflows/v41-train.yml`
starts the cloud pipeline. No local Python, Linux, JAX, compiler, or training
machine is required.

The workflow uses Python 3.12 and `pip install -e .` on `ubuntu-latest`. Bootstrap
builds the C++ runtime, runs the rollout/checkpoint tests, tries to restore the
newest compatible `v41-final-training-state` artifact from an earlier completed
run on the same PR branch, initializes a fresh production checkpoint only when no
compatible artifact exists, and runs an isolated tiny competition-engine smoke
test.

Twelve sequential jobs each restore the immediately preceding `v41-state-NN`
artifact and run one long Python/JAX collection process for at most 150 minutes.
The trainer checkpoints every completed game; there is no per-game Python/JAX
process startup. Jobs have a 180-minute timeout, leaving 30 minutes for setup and
artifact upload. The final job fits `policy.bin` once from all accumulated rollout
values.

Production collection uses the real `GeneralsEnv(mode="competition")` ruleset,
feature schema v2 shared exactly with the C++ runtime, four continuation rollouts,
a 50-turn horizon, ten sampled states/game, and up to eight candidate actions.
The minimum gates are 5,000 games and 1,000,000 usable rollout-derived pairs. If
5,000 games are reached before the pair gate, collection may continue up to
10,000 games rather than becoming permanently unable to satisfy acceptance.

Important artifacts:

* `v41-state-NN`: same-run resumable intermediate state.
* `v41-final-training-state`: full cross-run resumable checkpoint and rollout data.
* `v41-final-handoff`: `manifest.json`, candidate `policy.bin`, and handoff ZIP.

The bootstrap restore helper uses only the repository-scoped `GITHUB_TOKEN` with
read permissions. It searches earlier completed runs of the same workflow and PR
head branch for `v41-final-training-state`, validates pack version 2, feature
schema 2, and `env_mode=competition`, and resumes only a compatible checkpoint.
Therefore a later PR synchronization run does not restart from game zero.

The workflow deliberately never copies its candidate over
`competition/agents/juraj_cpp/policy.bin` or `tactics.bin`. Binary model files are
outputs of training, not required inputs. A supervising agent must inspect the
manifest and run the separate validation/safety campaign before promotion.

Training seeds start at 10000. Validation (20000–21999) and held-out testing
(30000–31999) are intentionally outside this fitting workflow.
