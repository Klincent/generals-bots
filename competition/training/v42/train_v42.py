#!/usr/bin/env python3
"""Supervised V3.4 bootstrap trainer for the V4.2 neural policy/value bot."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np

from neural_v42 import DEFAULT_BLOCKS, DEFAULT_WIDTH, count_params, init_params, masked_logits

ARRAY_KEYS = ("types", "owners", "armies", "valid", "globals", "actions", "values", "seed")


def load_dataset(root: Path) -> dict[str, np.ndarray]:
    shards = sorted(root.glob("teacher-*.npz"))
    if not shards:
        raise SystemExit(f"no teacher shards in {root}")
    parts = {k: [] for k in ARRAY_KEYS}
    for path in shards:
        with np.load(path) as z:
            for k in ARRAY_KEYS:
                parts[k].append(np.asarray(z[k]))
    out = {k: np.concatenate(v, axis=0) for k, v in parts.items()}
    n = len(out["actions"])
    if any(len(out[k]) != n for k in ARRAY_KEYS):
        raise RuntimeError("dataset arrays have inconsistent lengths")
    return out


def split_masks(seeds: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Whole-game split; no observation from one game may occur in both sets.
    val = (seeds.astype(np.int64) % 10) == 0
    if not np.any(val) or np.all(val):
        unique = np.unique(seeds)
        if len(unique) < 2:
            raise SystemExit("need at least two game seeds for train/validation split")
        val = seeds == unique[-1]
    return ~val, val


def _batch(data: dict[str, np.ndarray], indices: np.ndarray) -> dict[str, jnp.ndarray]:
    return {k: jnp.asarray(data[k][indices]) for k in ("types", "owners", "armies", "valid", "globals")}


def _loss_and_metrics(params, batch, labels, targets, value_weight: float):
    logits, value, _ = masked_logits(params, batch)
    logp = jax.nn.log_softmax(logits, axis=-1)
    rows = jnp.arange(labels.shape[0])
    policy_loss = -jnp.mean(logp[rows, labels])
    value_mse = jnp.mean(jnp.square(value - targets))
    loss = policy_loss + value_weight * value_mse
    top1 = jnp.mean(jnp.argmax(logits, axis=-1) == labels)
    top5_idx = jax.lax.top_k(logits, 5)[1]
    top5 = jnp.mean(jnp.any(top5_idx == labels[:, None], axis=-1))
    return loss, (policy_loss, value_mse, top1, top5)


def _zeros_like(tree):
    return jax.tree_util.tree_map(jnp.zeros_like, tree)


def adam_update(params, grads, m, v, step: jnp.ndarray, lr: float,
                beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8):
    m = jax.tree_util.tree_map(lambda mm, g: beta1 * mm + (1.0 - beta1) * g, m, grads)
    v = jax.tree_util.tree_map(lambda vv, g: beta2 * vv + (1.0 - beta2) * jnp.square(g), v, grads)
    bc1 = 1.0 - beta1 ** step
    bc2 = 1.0 - beta2 ** step
    params = jax.tree_util.tree_map(
        lambda p, mm, vv: p - lr * (mm / bc1) / (jnp.sqrt(vv / bc2) + eps),
        params, m, v,
    )
    return params, m, v


def save_checkpoint(path: Path, params, width: int, blocks: int, report: dict) -> None:
    leaves, _ = jax.tree_util.tree_flatten(params)
    arrays = {f"p{i:03d}": np.asarray(x, dtype=np.float32) for i, x in enumerate(leaves)}
    arrays["meta"] = np.asarray(json.dumps({
        "schema": 1,
        "width": width,
        "blocks": blocks,
        "leaf_count": len(leaves),
        "report": report,
    }, sort_keys=True))
    with path.open("wb") as fh:
        np.savez(fh, **arrays)


def evaluate(params, data, indices: np.ndarray, batch_size: int, value_weight: float) -> dict:
    totals = np.zeros(5, dtype=np.float64)
    seen = 0
    for start in range(0, len(indices), batch_size):
        ii = indices[start:start + batch_size]
        b = _batch(data, ii)
        labels = jnp.asarray(data["actions"][ii], dtype=jnp.int32)
        values = jnp.asarray(data["values"][ii], dtype=jnp.float32)
        loss, m = _loss_and_metrics(params, b, labels, values, value_weight)
        vals = np.asarray((loss,) + m, dtype=np.float64)
        totals += vals * len(ii)
        seen += len(ii)
    avg = totals / max(seen, 1)
    return {
        "loss": float(avg[0]),
        "policy_loss": float(avg[1]),
        "value_mse": float(avg[2]),
        "top1": float(avg[3]),
        "top5": float(avg[4]),
        "samples": int(seen),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--learning-rate", type=float, default=3e-4)
    p.add_argument("--value-weight", type=float, default=0.25)
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--blocks", type=int, default=DEFAULT_BLOCKS)
    p.add_argument("--seed", type=int, default=42042)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    data = load_dataset(args.data)
    train_mask, val_mask = split_masks(data["seed"])
    train_idx = np.flatnonzero(train_mask)
    val_idx = np.flatnonzero(val_mask)
    train_seeds = sorted(map(int, np.unique(data["seed"][train_idx])))
    val_seeds = sorted(map(int, np.unique(data["seed"][val_idx])))

    params = init_params(jax.random.PRNGKey(args.seed), args.width, args.blocks)
    m, v = _zeros_like(params), _zeros_like(params)
    step = 0

    @jax.jit
    def train_step(params, m, v, step, batch, labels, targets):
        (loss, metrics), grads = jax.value_and_grad(_loss_and_metrics, has_aux=True)(
            params, batch, labels, targets, args.value_weight
        )
        params, m, v = adam_update(params, grads, m, v, step, args.learning_rate)
        return params, m, v, loss, metrics

    rng = np.random.default_rng(args.seed)
    history = []
    for epoch in range(1, args.epochs + 1):
        perm = rng.permutation(train_idx)
        accum = np.zeros(5, dtype=np.float64)
        seen = 0
        for start in range(0, len(perm) - args.batch_size + 1, args.batch_size):
            ii = perm[start:start + args.batch_size]
            step += 1
            params, m, v, loss, metrics = train_step(
                params, m, v, jnp.asarray(step, dtype=jnp.float32), _batch(data, ii),
                jnp.asarray(data["actions"][ii], dtype=jnp.int32),
                jnp.asarray(data["values"][ii], dtype=jnp.float32),
            )
            vals = np.asarray((loss,) + metrics, dtype=np.float64)
            accum += vals * len(ii)
            seen += len(ii)
        train = accum / max(seen, 1)
        val = evaluate(params, data, val_idx, args.batch_size, args.value_weight)
        row = {
            "epoch": epoch,
            "train": {
                "loss": float(train[0]), "policy_loss": float(train[1]),
                "value_mse": float(train[2]), "top1": float(train[3]), "top5": float(train[4]),
                "samples": int(seen),
            },
            "validation": val,
        }
        history.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)

    report = {
        "schema": 1,
        "model": {"width": args.width, "blocks": args.blocks, "params": count_params(params)},
        "optimizer": {"name": "adam", "learning_rate": args.learning_rate,
                      "batch_size": args.batch_size, "epochs": args.epochs,
                      "value_weight": args.value_weight, "steps": step},
        "dataset": {
            "samples": int(len(data["actions"])),
            "train_samples": int(len(train_idx)), "validation_samples": int(len(val_idx)),
            "train_seeds": train_seeds, "validation_seeds": val_seeds,
        },
        "history": history,
        "final_validation": history[-1]["validation"],
    }
    (args.out / "train-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    save_checkpoint(args.out / "model-v42.npz", params, args.width, args.blocks, report)
    print(json.dumps({"checkpoint": str(args.out / "model-v42.npz"),
                      "params": report["model"]["params"],
                      "final_validation": report["final_validation"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
