#!/usr/bin/env python3
"""Deterministic regularized pairwise fitter and V4.1 policy pack codec."""
from __future__ import annotations

import argparse
import gzip
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator

import numpy as np

MAGIC = b"JURAJV4\0"
PACK_VERSION = 3
POLICY_KIND = 1
FEATURE_SCHEMA_VERSION = 2
DTYPE_FLOAT32 = 1
HEADER = struct.Struct("<8s6I8I")


@dataclass(frozen=True)
class Pair:
    seed: int
    positive: tuple[int, ...]
    negative: tuple[int, ...]
    delta: float


def validation_seed(seed: int, fraction: float = 0.2, salt: int = 0x41A9) -> bool:
    """Stable game-group split; every state/pair from one seed stays together."""
    if not 0.0 <= fraction < 1.0:
        raise ValueError("validation fraction must be in [0, 1)")
    # Integer arithmetic makes the split independent of Python/NumPy versions.
    x = (int(seed) ^ salt) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 30
    x = (x * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 27
    x = (x * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    x ^= x >> 31
    return x % 1_000_000 < int(fraction * 1_000_000)


def confidence_weight(delta: float, scale: float = 100.0, maximum: float = 4.0) -> float:
    """Map arbitrary rollout deltas to [1, maximum) without changing labels."""
    if scale <= 0 or maximum < 1 or not math.isfinite(delta):
        raise ValueError("invalid confidence input/configuration")
    return 1.0 + (maximum - 1.0) * math.tanh(abs(delta) / scale)


def read_pairs(path: Path, hash_size: int) -> Iterator[Pair]:
    mask = hash_size - 1
    if hash_size <= 0 or hash_size & mask:
        raise ValueError("hash size must be a power of two")
    with gzip.open(path, "rt") as source:
        for line in source:
            row = json.loads(line)
            seed = int(row["seed"])
            features = row["features"]
            for i, j, delta in row["pairs"]:
                a, b, d = features[i], features[j], float(delta)
                if d < 0:
                    a, b, d = b, a, -d
                if d:
                    yield Pair(seed, tuple(int(q) & mask for q in a),
                               tuple(int(q) & mask for q in b), d)


def audit_feature_hashes(path: Path, hash_size: int) -> dict:
    """Count actual collisions among feature hashes reachable in stored rows."""
    by_bucket: dict[int, set[int]] = {}
    states = comparisons = 0
    seeds: set[int] = set()
    with gzip.open(path, "rt") as source:
        for line in source:
            row = json.loads(line)
            states += 1
            comparisons += len(row["pairs"])
            seeds.add(int(row["seed"]))
            for candidate in row["features"]:
                for raw in candidate:
                    value = int(raw)
                    by_bucket.setdefault(value & (hash_size - 1), set()).add(value)
    collided = {bucket: values for bucket, values in by_bucket.items() if len(values) > 1}
    return {"states": states, "comparisons": comparisons, "game_seeds": len(seeds),
            "unique_feature_hashes": sum(len(values) for values in by_bucket.values()),
            "occupied_buckets": len(by_bucket), "collided_buckets": len(collided),
            "colliding_feature_hashes": sum(len(values) for values in collided.values())}


def _difference(pair: Pair) -> dict[int, int]:
    out: dict[int, int] = {}
    for index in pair.positive:
        out[index] = out.get(index, 0) + 1
    for index in pair.negative:
        out[index] = out.get(index, 0) - 1
    return {index: value for index, value in out.items() if value}


def _metrics(pairs: Iterable[Pair], weights: np.ndarray, l2: float) -> dict:
    loss = correct = count = weight_sum = margin_sum = probability_sum = 0.0
    for pair in pairs:
        diff = _difference(pair)
        margin = sum(weights[i] * value for i, value in diff.items())
        sample_weight = confidence_weight(pair.delta)
        loss += sample_weight * float(np.logaddexp(0.0, -margin))
        correct += sample_weight * (margin > 0.0)
        weight_sum += sample_weight
        margin_sum += sample_weight * margin
        probability_sum += sample_weight / (1.0 + math.exp(-max(-60.0, min(60.0, margin))))
        count += 1
    return {
        "pairs": int(count),
        "weighted_logistic_loss": loss / max(1.0, weight_sum) + 0.5 * l2 * float(weights @ weights),
        "weighted_accuracy": correct / max(1.0, weight_sum),
        "mean_signed_margin": margin_sum / max(1.0, weight_sum),
        "mean_preferred_probability": probability_sum / max(1.0, weight_sum),
        "sample_weight_sum": weight_sum,
    }


def fit_pairs(pairs: Iterable[Pair] | Callable[[], Iterable[Pair]], hash_size: int, *, epochs: int = 8,
              learning_rate: float = 0.05, l2: float = 1e-4,
              validation_fraction: float = 0.2) -> tuple[np.ndarray, np.ndarray, dict]:
    """Fit weighted pairwise logistic loss using deterministic full-batch Adam."""
    if callable(pairs):
        factory = pairs
    else:
        cached = tuple(pairs)
        factory = lambda: iter(cached)
    seeds = {pair.seed for pair in factory()}
    train_seeds = {seed for seed in seeds if not validation_seed(seed, validation_fraction)}
    validation_seeds = seeds - train_seeds
    if not train_seeds:
        raise ValueError("training split is empty")
    def split(validation: bool):
        selected = validation_seeds if validation else train_seeds
        return (pair for pair in factory() if pair.seed in selected)
    weights = np.zeros(hash_size, dtype=np.float64)
    coverage = np.zeros(hash_size, dtype=np.uint32)
    m = np.zeros_like(weights)
    v = np.zeros_like(weights)
    for step in range(1, epochs + 1):
        gradient = np.zeros_like(weights)
        total_weight = 0.0
        for pair in split(False):
            diff = _difference(pair)
            margin = sum(weights[i] * value for i, value in diff.items())
            sample_weight = confidence_weight(pair.delta)
            coefficient = -sample_weight / (1.0 + math.exp(max(-60.0, min(60.0, margin))))
            for index, value in diff.items():
                gradient[index] += coefficient * value
                if step == 1:
                    coverage[index] = min(np.iinfo(np.uint32).max, int(coverage[index]) + abs(value))
            total_weight += sample_weight
        gradient /= max(1.0, total_weight)
        gradient += l2 * weights
        m = 0.9 * m + 0.1 * gradient
        v = 0.999 * v + 0.001 * gradient * gradient
        mhat = m / (1.0 - 0.9**step)
        vhat = v / (1.0 - 0.999**step)
        weights -= learning_rate * mhat / (np.sqrt(vhat) + 1e-8)
    nonzero = np.abs(weights[np.nonzero(coverage)])
    report = {
        "format_version": PACK_VERSION,
        "feature_schema": FEATURE_SCHEMA_VERSION,
        "optimizer": {"name": "full_batch_adam", "epochs": epochs, "learning_rate": learning_rate,
                      "beta1": 0.9, "beta2": 0.999, "epsilon": 1e-8, "l2": l2},
        "confidence": {"formula": "1 + 3*tanh(abs(delta)/100)", "minimum": 1.0, "maximum_exclusive": 4.0},
        "split": {"unit": "game_seed", "validation_fraction": validation_fraction,
                  "train_seeds": len(train_seeds),
                  "validation_seeds": len(validation_seeds)},
        "train": _metrics(split(False), weights, l2),
        "validation": _metrics(split(True), weights, l2),
        "weights": {"nonzero": int(np.count_nonzero(weights)), "covered_buckets": int(np.count_nonzero(coverage)),
                    "max_abs": float(np.max(np.abs(weights))),
                    "abs_percentiles": {str(q): float(np.percentile(nonzero, q)) if nonzero.size else 0.0
                                        for q in (0, 25, 50, 75, 90, 95, 99, 100)}},
    }
    return weights.astype(np.float32), coverage, report


def _checksum(payload: bytes) -> int:
    value = 2166136261
    for byte in payload:
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def serialize_policy(weights: np.ndarray, coverage: np.ndarray, sample_count: int) -> bytes:
    w = np.asarray(weights, dtype="<f4")
    c = np.minimum(np.asarray(coverage), 255).astype("u1")
    if w.ndim != 1 or c.shape != w.shape or not np.isfinite(w).all() or not len(w) or len(w) & (len(w) - 1):
        raise ValueError("invalid policy arrays")
    payload = w.tobytes() + c.tobytes()
    reserved = [FEATURE_SCHEMA_VERSION, DTYPE_FLOAT32] + [0] * 6
    return HEADER.pack(MAGIC, PACK_VERSION, POLICY_KIND, int(sample_count), len(w),
                       len(payload), _checksum(payload), *reserved) + payload


def deserialize_policy(data: bytes) -> tuple[np.ndarray, np.ndarray, int]:
    if len(data) < HEADER.size:
        raise ValueError("truncated policy header")
    magic, version, kind, count, size, payload_bytes, checksum, *reserved = HEADER.unpack_from(data)
    if (magic != MAGIC or version != PACK_VERSION or kind != POLICY_KIND or
            reserved[:2] != [FEATURE_SCHEMA_VERSION, DTYPE_FLOAT32] or not size or size & (size - 1)):
        raise ValueError("incompatible policy header")
    payload = data[HEADER.size:]
    if payload_bytes != size * 5 or len(payload) != payload_bytes or _checksum(payload) != checksum:
        raise ValueError("corrupt policy payload")
    weights = np.frombuffer(payload[:size * 4], dtype="<f4").copy()
    if not np.isfinite(weights).all():
        raise ValueError("non-finite policy weight")
    return weights, np.frombuffer(payload[size * 4:], dtype="u1").copy(), count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--hash-bits", type=int, choices=(20, 21, 22), default=20)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--l2", type=float, default=1e-4)
    args = parser.parse_args()
    size = 1 << args.hash_bits
    weights, coverage, report = fit_pairs(lambda: read_pairs(args.rollouts, size), size, epochs=args.epochs,
                                          learning_rate=args.learning_rate, l2=args.l2)
    args.policy.write_bytes(serialize_policy(weights, coverage, report["train"]["pairs"]))
    report["policy_bytes"] = args.policy.stat().st_size
    report["data"] = audit_feature_hashes(args.rollouts, size)
    report["intervention_rate"] = None
    report["intervention_rate_reason"] = "runtime benchmark diagnostic; unavailable from pair records"
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
