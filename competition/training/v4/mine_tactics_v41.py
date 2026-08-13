#!/usr/bin/env python3
"""Targeted tactical miner for V4.1 using real competition states.

This intentionally does not derive tactics from the completed general rollout
artifact: those rows do not contain enough state to reproduce a runtime tactic
key. Instead we sample contact/combat states from GeneralsEnv(mode='competition')
and evaluate candidate actions with common-seed short rollouts.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import jax.numpy as jnp
import numpy as np

from generals import GeneralsEnv
from matchup import make_board, make_transition
from rollout_train import (candidates, clone_state, feature_context, policy,
                           rollout)
from tactics_v41 import TacticRecord, serialize_tactics, tactic_key

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _key_for(ctx: dict, action) -> int | None:
    if action[0]:
        return None
    _, r, c, d, split = action
    dr, dc = DIRS[d]
    y, x = r + dr, c + dc
    src = r * ctx["w"] + c
    dst = y * ctx["w"] + x
    return tactic_key(
        dest_owner=int(ctx["owners"][y, x]),
        dest_type=int(ctx["types"][y, x]),
        source_army=int(ctx["armies"][r, c]),
        dest_army=int(ctx["armies"][y, x]),
        split=bool(split),
        own_general_distance=int(ctx["dist_own"][dst]),
        enemy_general_visible=bool(ctx["enemy_visible"]),
        contact_visible=bool(ctx["contact_visible"]),
        source_degree=int(ctx["degree"][src]),
        dest_degree=int(ctx["degree"][dst]),
    )


def mine(*, seed_start: int, games: int, states_per_game: int,
         rollouts_per_action: int, horizon: int, candidate_count: int,
         min_support: int) -> tuple[list[TacticRecord], dict]:
    env = GeneralsEnv(mode="competition")
    step = make_transition(env)
    sums: dict[int, float] = defaultdict(float)
    visits: dict[int, int] = defaultdict(int)
    sampled_states = evaluated_actions = contact_states = 0

    for gi in range(games):
        seed = seed_start + gi
        state = make_board(env, seed)
        rng = np.random.default_rng(seed ^ 0x41A9)
        player = gi & 1
        chosen = 0
        max_turn = min(500, int(getattr(env, "truncation", 1200) or 1200) - 1)
        for turn in range(max_turn):
            if int(state.winner) >= 0:
                break
            ctx = feature_context(state, player)
            # Tactical mining is intentionally concentrated on observed contact,
            # visible enemy information, or contested destinations.
            cs = candidates(state, player, candidate_count)
            contested = any((not a[0]) and int(ctx["owners"][a[1] + DIRS[a[3]][0],
                                                             a[2] + DIRS[a[3]][1]]) == 2
                            for a in cs)
            interesting = ctx["contact_visible"] or ctx["enemy_visible"] or contested
            if interesting and chosen < states_per_game:
                contact_states += 1
                keys = [_key_for(ctx, action) for action in cs]
                scores = []
                for ai, action in enumerate(cs):
                    vals = [rollout(step, state, player, action,
                                    seed * 100000 + chosen * 1000 + k,
                                    horizon, (gi + k) % 9)
                            for k in range(rollouts_per_action)]
                    scores.append(float(np.mean(vals)))
                    evaluated_actions += 1
                center = float(np.median(scores))
                for key, score in zip(keys, scores):
                    if key is None:
                        continue
                    # Runtime divides tactic value by 8. Store a bounded score
                    # offset so the learned tactical term remains secondary to
                    # hard V3.4 safety and ordinary candidate scoring.
                    value = max(-32768.0, min(32767.0, 8.0 * (score - center)))
                    sums[key] += value
                    visits[key] += 1
                sampled_states += 1
                chosen += 1
            acts = [policy(state, 0, rng, gi % 9),
                    policy(state, 1, rng, (gi + 4) % 9)]
            state, _ = step(state, jnp.asarray(acts, dtype=jnp.int32))
            if chosen >= states_per_game:
                break

    rows = [TacticRecord(key, int(round(sums[key] / visits[key])), min(65535, visits[key]))
            for key in sorted(visits) if visits[key] >= min_support]
    support = sorted(visits.values())
    report = {
        "schema": 1,
        "environment": "competition",
        "seed_start": seed_start,
        "games": games,
        "sampled_states": sampled_states,
        "contact_or_combat_states_seen": contact_states,
        "evaluated_actions": evaluated_actions,
        "rollouts_per_action": rollouts_per_action,
        "horizon": horizon,
        "candidate_count": candidate_count,
        "minimum_support": min_support,
        "unique_keys_before_filter": len(visits),
        "records_after_filter": len(rows),
        "support": {
            "min": min(support) if support else 0,
            "median": float(np.median(support)) if support else 0.0,
            "max": max(support) if support else 0,
        },
    }
    return rows, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tactics", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, default=41000)
    parser.add_argument("--games", type=int, default=64)
    parser.add_argument("--states-per-game", type=int, default=3)
    parser.add_argument("--rollouts-per-action", type=int, default=4)
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--candidates", type=int, default=8)
    parser.add_argument("--min-support", type=int, default=3)
    args = parser.parse_args()
    rows, report = mine(seed_start=args.seed_start, games=args.games,
                        states_per_game=args.states_per_game,
                        rollouts_per_action=args.rollouts_per_action,
                        horizon=args.horizon, candidate_count=args.candidates,
                        min_support=args.min_support)
    args.tactics.write_bytes(serialize_tactics(rows))
    report["tactics_bytes"] = args.tactics.stat().st_size
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
