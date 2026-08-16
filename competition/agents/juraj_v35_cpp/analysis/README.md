# V3.5 diagnostic analysis

These utilities are intentionally outside the production agent. They replay
**used** seeds and do not alter candidate selection or gameplay.

1. Run `paired_benchmark.py` for castle-only and recovery variants with the
   same candidate/baseline materialization.
2. Run `causal_ab.py` on the two `games.jsonl` files.
3. Run `replay_losses.py` on the recovery `games.jsonl`. It passes
   `--diagnostic-json` to `competition/matchup.py`, which records pre-action
   full state and both emitted actions without changing the transition.
4. Run `loss_forensics.py` to produce the all-loss evidence table.
5. Run `render_report.py` to render the Markdown appendix.

The trace deliberately distinguishes protocol/state facts from unavailable
agent internals. In particular, a production summary does not emit every
candidate, rejected alternative, packet objective, or per-turn reason. The
forensics tool marks those questions unobservable instead of inventing a
causal label.

Protected validation ranges `22100..22119` and `22150..22199`, and held-out
range `30000..30499`, must not be passed to these used-seed tools.
