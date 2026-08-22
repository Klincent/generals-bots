#!/usr/bin/env python3
"""Replay every loss from a used paired benchmark with full diagnostic frames."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    losses = [json.loads(line) for line in a.games.read_text().splitlines()
              if json.loads(line).get("result") == "loss"]
    forbidden = [x["seed"] for x in losses if 22100 <= x["seed"] <= 22199
                 or 30000 <= x["seed"] <= 30499]
    if forbidden:
        raise SystemExit(f"refusing protected/final-heldout seeds: {sorted(set(forbidden))}")
    for index, game in enumerate(losses, 1):
        seed, seat = game["seed"], game["candidate_seat"]
        trace = a.output / f"trace-{seed}-{seat}.json"
        audit = a.output / f"audit-{seed}-{seat}.json"
        if trace.exists() and audit.exists():
            continue
        agents = [a.candidate, a.baseline] if seat == 0 else [a.baseline, a.candidate]
        env = os.environ.copy()
        env["JURAJ_RNG_SEED"] = str(game["rng_seed"])
        env["JURAJ_V35_TRACE"] = "1"
        print(f"[{index}/{len(losses)}] seed={seed} seat={seat}", flush=True)
        subprocess.run([sys.executable, "competition/matchup.py",
                        *map(str, agents), "--mode", "competition", "--seed", str(seed),
                        "--audit-json", str(audit), "--diagnostic-json", str(trace)],
                       check=True, env=env, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
