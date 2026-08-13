#!/usr/bin/env python3
"""Aggregate V4.1 paired-map benchmark JSONL and compute paired bootstrap CI."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


def game_score(result: str) -> float:
    return {"win": 1.0, "draw": 0.5, "loss": 0.0}[result]


def summarize(rows: list[dict], bootstrap_samples: int = 10000,
              bootstrap_seed: int = 0x41A9) -> dict:
    ok = [r for r in rows if r.get("status") == "ok" and r.get("result") in {"win", "draw", "loss"}]
    errors = [r for r in rows if r not in ok]
    counts = Counter(r["result"] for r in ok)
    score = float(np.mean([game_score(r["result"]) for r in ok])) if ok else None

    seat = {}
    for s in (0, 1):
        part = [r for r in ok if int(r["candidate_seat"]) == s]
        seat[str(s)] = {
            "games": len(part),
            "wins": sum(r["result"] == "win" for r in part),
            "draws": sum(r["result"] == "draw" for r in part),
            "losses": sum(r["result"] == "loss" for r in part),
            "score": float(np.mean([game_score(r["result"]) for r in part])) if part else None,
        }

    by_seed: dict[int, list[dict]] = defaultdict(list)
    for row in ok:
        by_seed[int(row["seed"])].append(row)
    paired = []
    incomplete = []
    for seed_value in sorted({int(r["seed"]) for r in rows}):
        pair = by_seed.get(seed_value, [])
        seats = {int(r["candidate_seat"]) for r in pair}
        if len(pair) == 2 and seats == {0, 1}:
            pair_score = float(np.mean([game_score(r["result"]) for r in pair]))
            paired.append({"seed": seed_value, "score": pair_score,
                           "results": {str(r["candidate_seat"]): r["result"] for r in pair}})
        else:
            incomplete.append(seed_value)

    ci = None
    if paired:
        values = np.asarray([p["score"] for p in paired], dtype=np.float64)
        rng = np.random.default_rng(bootstrap_seed)
        draws = rng.integers(0, len(values), size=(bootstrap_samples, len(values)))
        samples = values[draws].mean(axis=1)
        ci = {
            "low": float(np.percentile(samples, 2.5)),
            "high": float(np.percentile(samples, 97.5)),
            "samples": bootstrap_samples,
            "seed": bootstrap_seed,
        }

    walls = np.asarray([float(r["wall_seconds"]) for r in ok], dtype=np.float64)
    turns = np.asarray([int(r["turns"]) for r in ok if r.get("turns") is not None], dtype=np.float64)
    timing = {
        "wall_seconds_p50": float(np.percentile(walls, 50)) if walls.size else None,
        "wall_seconds_p95": float(np.percentile(walls, 95)) if walls.size else None,
        "wall_seconds_p99": float(np.percentile(walls, 99)) if walls.size else None,
        "wall_seconds_max": float(walls.max()) if walls.size else None,
        "turns_p50": float(np.percentile(turns, 50)) if turns.size else None,
        "turns_p95": float(np.percentile(turns, 95)) if turns.size else None,
        "turns_max": int(turns.max()) if turns.size else None,
    }
    error_counts = Counter(r.get("status", "unknown") for r in errors)
    return {
        "games_total_rows": len(rows),
        "games_scored": len(ok),
        "wins": counts["win"],
        "draws": counts["draw"],
        "losses": counts["loss"],
        "score": score,
        "seat_split": seat,
        "paired_seed_count": len(paired),
        "paired_bootstrap_95ci": ci,
        "paired_maps": paired,
        "incomplete_seeds": incomplete,
        "errors": dict(sorted(error_counts.items())),
        "timing": timing,
        "acceptance_ready": len(errors) == 0 and not incomplete,
    }


def load_rows(paths: list[Path]) -> list[dict]:
    rows = []
    seen = set()
    for path in paths:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (int(row["seed"]), int(row["candidate_seat"]))
            if key in seen:
                raise ValueError(f"duplicate benchmark game {key}")
            seen.add(key)
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    args = parser.parse_args()
    summary = summarize(load_rows(args.inputs), args.bootstrap_samples)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
