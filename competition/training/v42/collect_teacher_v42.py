#!/usr/bin/env python3
"""Collect exact corrected-V3.4 self-play demonstrations for V4.2."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

import jax.numpy as jnp
import numpy as np

from generals import GeneralsEnv
from generals.core import game
from matchup import ask_agent, close_agent, make_board, make_transition, spawn_agent
from neural_v42 import action_to_index, legal_action_mask, pad_observation


def _stack(rows: list[dict]) -> dict[str, np.ndarray]:
    return {k: np.stack([r[k] for r in rows]) for k in ("types", "owners", "armies", "valid", "globals")}


def _atomic_npz(path: Path, **arrays) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as fh:
        np.savez_compressed(fh, **arrays)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def collect_game(env: GeneralsEnv, teacher: Path, seed: int, sample_every: int) -> dict:
    state = make_board(env, seed)
    h, w = (int(x) for x in state.armies.shape)
    transition = make_transition(env)
    old_rng = os.environ.get("JURAJ_RNG_SEED")
    os.environ["JURAJ_RNG_SEED"] = str((seed * 0x9E3779B1 + 17) & 0x7FFFFFFF)
    agents = []
    rows: list[dict] = []
    action_indices: list[int] = []
    players: list[int] = []
    offset = seed % sample_every
    try:
        agents = [
            spawn_agent(teacher, 0, h, w, "v34-teacher-p0"),
            spawn_agent(teacher, 1, h, w, "v34-teacher-p1"),
        ]
        for turn in range(env.truncation):
            obs = [game.get_observation(state, p) for p in (0, 1)]
            actions = [ask_agent(agents[p], obs[p]) for p in (0, 1)]
            if turn % sample_every == offset:
                for p in (0, 1):
                    rows.append(pad_observation(obs[p]))
                    action_indices.append(action_to_index(np.asarray(actions[p])))
                    players.append(p)
            state, _ = transition(state, jnp.asarray(actions, dtype=jnp.int32))
            if int(state.winner) >= 0:
                break
    finally:
        for proc in agents:
            close_agent(proc)
        if old_rng is None:
            os.environ.pop("JURAJ_RNG_SEED", None)
        else:
            os.environ["JURAJ_RNG_SEED"] = old_rng

    winner = int(state.winner)
    values = np.asarray([
        0.0 if winner < 0 else (1.0 if p == winner else -1.0)
        for p in players
    ], dtype=np.float32)
    batch = _stack(rows)
    labels = np.asarray(action_indices, dtype=np.int32)
    legal = np.asarray(legal_action_mask(batch))
    bad = np.flatnonzero(~legal[np.arange(len(labels)), labels])
    if bad.size:
        i = int(bad[0])
        raise RuntimeError(f"teacher emitted action outside known-legal mask: sample={i} label={labels[i]}")

    kinds = Counter()
    for idx in labels:
        if idx == 21 * 21 * 9:
            kinds["pass"] += 1
        else:
            ch = int(idx) % 9
            kinds["build" if ch == 8 else ("half" if ch & 1 else "full")] += 1
    return batch | {
        "actions": labels,
        "values": values,
        "players": np.asarray(players, dtype=np.uint8),
        "seed": np.full((len(labels),), seed, dtype=np.int32),
        "winner": np.asarray(winner, dtype=np.int8),
        "turns": np.asarray(int(state.time), dtype=np.int16),
        "action_counts": dict(kinds),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--teacher-run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed-start", type=int, default=50000)
    p.add_argument("--games", type=int, default=32)
    p.add_argument("--sample-every", type=int, default=4)
    args = p.parse_args()
    if args.sample_every <= 0:
        raise SystemExit("sample-every must be positive")
    args.out.mkdir(parents=True, exist_ok=True)
    env = GeneralsEnv(mode="competition")

    manifest = {
        "schema": 1,
        "env_mode": "competition",
        "teacher": "exact-corrected-v3.4",
        "seed_start": args.seed_start,
        "requested_games": args.games,
        "sample_every": args.sample_every,
        "games": 0,
        "samples": 0,
        "wins_p0": 0,
        "wins_p1": 0,
        "draws": 0,
        "action_counts": {},
    }
    total_actions = Counter()
    for seed in range(args.seed_start, args.seed_start + args.games):
        shard = args.out / f"teacher-{seed}.npz"
        if shard.exists():
            with np.load(shard) as z:
                n = len(z["actions"])
                winner = int(z["winner"])
                labels = z["actions"]
            counts = Counter()
            for idx in labels:
                if int(idx) == 21 * 21 * 9:
                    counts["pass"] += 1
                else:
                    ch = int(idx) % 9
                    counts["build" if ch == 8 else ("half" if ch & 1 else "full")] += 1
        else:
            result = collect_game(env, args.teacher_run.resolve(), seed, args.sample_every)
            counts = Counter(result.pop("action_counts"))
            n = len(result["actions"])
            winner = int(result["winner"])
            _atomic_npz(shard, **result)
        manifest["games"] += 1
        manifest["samples"] += n
        if winner == 0:
            manifest["wins_p0"] += 1
        elif winner == 1:
            manifest["wins_p1"] += 1
        else:
            manifest["draws"] += 1
        total_actions.update(counts)
        manifest["action_counts"] = dict(total_actions)
        (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"seed": seed, "samples": n, "winner": winner, "actions": dict(counts)}, sort_keys=True), flush=True)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
