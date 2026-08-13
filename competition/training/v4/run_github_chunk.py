#!/usr/bin/env python3
"""Run one long, in-process V4.1 rollout-training chunk and fit once at the end."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def completed(checkpoint: Path) -> int:
    if not checkpoint.exists():
        return 0
    return int(json.loads(checkpoint.read_text()).get("games", 0))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--target-games", type=int, required=True)
    parser.add_argument("--target-pairs", type=int, default=1_000_000)
    parser.add_argument("--max-games", type=int, default=10000)
    parser.add_argument("--seed-start", type=int, default=10000)
    parser.add_argument("--max-minutes", type=float, default=150)
    parser.add_argument("--rollouts", type=int, default=4)
    parser.add_argument("--horizon", type=int, default=50)
    parser.add_argument("--states-per-game", type=int, default=10)
    parser.add_argument("--candidates", type=int, default=8)
    parser.add_argument("--hash-bits", type=int, default=20)
    parser.add_argument("--fit", action="store_true", help="fit policy.bin after collection")
    args = parser.parse_args()
    args.state_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = args.state_dir / "checkpoint.json"
    before = completed(checkpoint)

    env = os.environ.copy()
    env["PYTHONPATH"] = ".:competition:competition/training/v4"
    # One Python/JAX process now owns the whole chunk; no per-game interpreter/JIT
    # startup.  rollout_train.py checkpoints each completed game atomically and
    # voluntarily stops before this chunk's wall-clock budget is exhausted.
    collect = [
        sys.executable,
        "competition/training/v4/rollout_train.py",
        "--out", str(args.state_dir),
        "--games", str(args.target_games),
        "--target-pairs", str(args.target_pairs),
        "--max-games", str(args.max_games),
        "--seed-start", str(args.seed_start),
        "--rollouts", str(args.rollouts),
        "--horizon", str(args.horizon),
        "--states-per-game", str(args.states_per_game),
        "--candidates", str(args.candidates),
        "--hash-bits", str(args.hash_bits),
        "--max-wall-minutes", str(args.max_minutes),
        "--collect-only",
    ]
    subprocess.run(collect, check=True, env=env)

    after = completed(checkpoint)
    if args.fit and after:
        fit = [
            sys.executable,
            "competition/training/v4/rollout_train.py",
            "--out", str(args.state_dir),
            "--games", str(args.target_games),
            "--target-pairs", str(args.target_pairs),
            "--max-games", str(args.max_games),
            "--seed-start", str(args.seed_start),
            "--rollouts", str(args.rollouts),
            "--horizon", str(args.horizon),
            "--states-per-game", str(args.states_per_game),
            "--candidates", str(args.candidates),
            "--hash-bits", str(args.hash_bits),
            "--fit-only",
        ]
        subprocess.run(fit, check=True, env=env)

    summary = json.loads(checkpoint.read_text()) if checkpoint.exists() else {"games": 0}
    summary.update(
        {
            "chunk_target": args.target_games,
            "chunk_start_games": before,
            "chunk_end_games": after,
            "chunk_games_added": after - before,
            "target_reached": after >= args.target_games and int(summary.get("usable_pairs", 0)) >= args.target_pairs,
        }
    )
    (args.state_dir / "chunk-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
