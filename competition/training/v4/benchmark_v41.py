#!/usr/bin/env python3
"""Run paired held-out V3.4-vs-V4.1 matches through the real stdio runner."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

CAPTURE_RE = re.compile(r"\[matchup\] turn (\d+): player (\d+) captured the enemy general")
DRAW_RE = re.compile(r"\[matchup\] turn (\d+): truncated at (\d+) turns \(draw\)")
CASTLE_RE = re.compile(r"\[matchup\] castles built: (\d+) .* vs (\d+)")


def run_game(matchup: Path, baseline: Path, candidate: Path, seed: int,
             candidate_seat: int, timeout_seconds: float) -> dict:
    agent0, agent1 = ((candidate, baseline) if candidate_seat == 0
                      else (baseline, candidate))
    command = [sys.executable, str(matchup), str(agent0), str(agent1),
               "--mode", "competition", "--seed", str(seed)]
    started = time.perf_counter()
    try:
        proc = subprocess.run(command, text=True, capture_output=True,
                              timeout=timeout_seconds)
        elapsed = time.perf_counter() - started
    except subprocess.TimeoutExpired as exc:
        return {
            "seed": seed, "candidate_seat": candidate_seat,
            "status": "timeout", "result": None,
            "wall_seconds": time.perf_counter() - started,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }

    row = {
        "seed": seed,
        "candidate_seat": candidate_seat,
        "status": "ok" if proc.returncode == 0 else "process_error",
        "returncode": proc.returncode,
        "result": None,
        "turns": None,
        "wall_seconds": elapsed,
        "candidate_castles": None,
        "baseline_castles": None,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }
    if proc.returncode != 0:
        return row

    captured = CAPTURE_RE.search(proc.stdout)
    draw = DRAW_RE.search(proc.stdout)
    if captured:
        row["turns"] = int(captured.group(1))
        winner = int(captured.group(2))
        row["result"] = "win" if winner == candidate_seat else "loss"
    elif draw:
        row["turns"] = int(draw.group(1))
        row["result"] = "draw"
    else:
        row["status"] = "protocol_error"

    castles = CASTLE_RE.search(proc.stdout)
    if castles:
        p0, p1 = int(castles.group(1)), int(castles.group(2))
        row["candidate_castles"] = p0 if candidate_seat == 0 else p1
        row["baseline_castles"] = p1 if candidate_seat == 0 else p0
    return row


def completed_keys(path: Path) -> set[tuple[int, int]]:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        keys.add((int(row["seed"]), int(row["candidate_seat"])))
    return keys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-run", type=Path, required=True)
    parser.add_argument("--candidate-run", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=30000)
    parser.add_argument("--seed-end", type=int, default=30499)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    args = parser.parse_args()
    if args.seed_end < args.seed_start:
        raise SystemExit("seed-end must be >= seed-start")
    for path in (args.baseline_run, args.candidate_run):
        if not path.is_file():
            raise SystemExit(f"agent run script missing: {path}")

    matchup = Path(__file__).resolve().parents[2] / "matchup.py"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    done = completed_keys(args.output)
    with args.output.open("a", buffering=1) as out:
        for seed in range(args.seed_start, args.seed_end + 1):
            for candidate_seat in (0, 1):
                if (seed, candidate_seat) in done:
                    continue
                row = run_game(matchup, args.baseline_run.resolve(),
                               args.candidate_run.resolve(), seed,
                               candidate_seat, args.timeout_seconds)
                out.write(json.dumps(row, sort_keys=True) + "\n")
                print(json.dumps({k: row.get(k) for k in
                                  ("seed", "candidate_seat", "status", "result", "turns")},
                                 sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
