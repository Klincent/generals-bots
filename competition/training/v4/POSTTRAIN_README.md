# V4.1 post-training

Phase 1 replaces the collection-time integer vote accumulator with a deterministic
pairwise logistic ranker. The completed `rollouts.jsonl.gz` is an input and must
not be regenerated.

```bash
PYTHONPATH=competition/training/v4 python competition/training/v4/fit_policy_v41.py \
  --rollouts /path/to/rollouts.jsonl.gz \
  --policy /path/to/policy.bin \
  --report /path/to/policy-report.json
```

The split unit is the game seed. Training uses deterministic full-batch Adam on
weighted pairwise logistic loss with L2 regularization. Sample confidence is
bounded as `1 + 3*tanh(abs(delta)/100)`, so a terminal delta cannot create an
unbounded gradient.

Policy pack version 3 contains a 64-byte little-endian header followed by one
float32 per hash bucket and one saturated uint8 coverage counter per bucket.
Header reserved fields identify feature schema 2 and float32 encoding. The
runtime rejects wrong versions/schemas, malformed sizes, bad checksums, and
non-finite weights. A rejected or missing policy leaves the V3.4 baseline choice
unchanged.

`policy-report.json` contains optimizer configuration, seed split sizes, weighted
train/validation loss and accuracy, preferred-action probability and margin,
coverage, and weight percentiles. Runtime intervention rate remains a benchmark
diagnostic and is explicitly marked unavailable during fitting. Phase 2 still
needs the honest tactics miner and the held-out benchmark workflow.
