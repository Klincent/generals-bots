# Codex repository guidance

This repository contains competitive game-playing agents. Treat benchmark results as the source of truth: a change that looks locally cleaner is not an improvement unless it preserves or improves competitive performance.

## Read first

Before modifying the Juraj bot, read:

- `competition/agents/juraj_v35_cpp/AGENTS.md`
- `docs/codex/CURRENT_TASK.md`
- `docs/codex/RESULTS.md`

The nested `AGENTS.md` contains bot-specific invariants and overrides this file for that subtree.

## General engineering rules

- Prefer the smallest coherent change that solves the stated problem.
- Do not rewrite a working subsystem just because another design looks cleaner.
- Preserve behavior outside the scenario the task explicitly targets.
- Inspect the existing architecture before implementing. Integrate with it; do not bolt on a parallel scheduler or duplicate state machine without strong evidence.
- Avoid string-replacement patching as the final implementation method. Edit the C++ source coherently and leave readable, maintainable code.
- Every strategic change must be paired with focused regression tests and a paired benchmark against the exact requested baseline.
- Use identical seeds and both seats for competitive comparisons.
- Never infer improvement from a tiny sample. Report W/D/L, score, errors/illegal actions and confidence/uncertainty when available.
- Inspect losses and telemetry, not only aggregate score.
- If a requested feature causes a material regression, do not hide it or combine it with other changes. Isolate the cause first.
- Do not merge to `master` unless explicitly asked. Work on a feature branch and leave a clean committed state.

## Validation

For the Juraj C++ agent, the normal minimum validation is:

```bash
bash competition/agents/juraj_v35_cpp/test.sh
bash competition/agents/juraj_v35_cpp/build.sh
```

Competitive tasks must additionally run the paired benchmark specified in `docs/codex/CURRENT_TASK.md`.

## Reporting

At the end of a task:

1. update `docs/codex/RESULTS.md` with the tested commit(s), exact baseline, seed ranges, W/D/L, score and key telemetry;
2. state exactly which files changed and why;
3. state any known regressions or unresolved questions;
4. provide the final branch and commit SHA.
