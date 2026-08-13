#!/usr/bin/env python3
"""Resumable V4.1 same-state rollout trainer using the real competition ruleset.

The policy pack written here uses feature schema v2.  The same schema is hard-coded
in juraj_cpp/main.cpp.  V4.0/v1 packs are intentionally rejected by the V4.1
runtime so an old model can never be interpreted with new feature semantics.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import time
from collections import deque
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np
from fit_policy_v41 import (FEATURE_SCHEMA_VERSION, PACK_VERSION,
                            audit_feature_hashes, fit_pairs, read_pairs,
                            serialize_policy)
from generals import GeneralsEnv
from generals.core import game
from matchup import make_board, make_transition

MASK = (1 << 64) - 1
DEFAULT_CANDIDATES = 8


def mix(x: int) -> int:
    x = (x + 0x9E3779B97F4A7C15) & MASK
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK
    return x ^ (x >> 31)


def bucket(a: int) -> int:
    if a <= 1:
        return 0
    if a <= 3:
        return 1
    if a <= 7:
        return 2
    if a <= 15:
        return 3
    if a <= 31:
        return 4
    if a <= 63:
        return 5
    if a <= 127:
        return 6
    return 7


def clone_state(s):
    return jax.tree.map(lambda x: jnp.array(np.array(x), copy=True), s)


def legal(s, p: int):
    own = np.asarray(s.ownership[p])
    army = np.asarray(s.armies)
    pas = np.asarray(s.passable)
    h, w = army.shape
    out = [(1, 0, 0, 0, 0)]
    for r, c in zip(*np.where(own & (army > 1))):
        for d, (dr, dc) in enumerate(((-1, 0), (1, 0), (0, -1), (0, 1))):
            y, x = int(r) + dr, int(c) + dc
            if 0 <= y < h and 0 <= x < w and pas[y, x]:
                # FULL-1 is the normal V3/V4 road action.  Rollout alternatives
                # remain bounded and do not add gratuitous HALF variants here.
                out.append((0, int(r), int(c), d, 0))
    return out


def candidates(s, p: int, n: int = DEFAULT_CANDIDATES):
    own = np.asarray(s.ownership[p])
    opp = np.asarray(s.ownership[1 - p])
    a = np.asarray(s.armies)
    rank = []
    for z in legal(s, p):
        if z[0]:
            rank.append((-1.0, z))
            continue
        _, r, c, d, _ = z
        dr, dc = ((-1, 0), (1, 0), (0, -1), (0, 1))[d]
        y, x = r + dr, c + dc
        moved = int(a[r, c]) - 1
        score = (
            (500 if opp[y, x] and moved > int(a[y, x]) else 0)
            + (80 if not own[y, x] else 0)
            + 3 * moved
            + (int(a[y, x]) if own[y, x] else 0)
        )
        rank.append((float(score), z))
    rank.sort(reverse=True)

    out = []
    source_counts: dict[tuple[int, int], int] = {}
    for _, z in rank:
        src = (z[1], z[2]) if not z[0] else (-1, -1)
        # Preserve source diversity, but permit a second route from a high-value
        # source once several distinct packets are already represented.
        count = source_counts.get(src, 0)
        if src != (-1, -1) and count >= 1 and len(source_counts) < 4:
            continue
        if count >= 2:
            continue
        out.append(z)
        source_counts[src] = count + 1
        if len(out) >= n:
            break
    return out


def policy(s, p: int, rng: np.random.Generator, style: int):
    """Cheap diverse continuation policy; engine legality remains authoritative."""
    aa = legal(s, p)
    if len(aa) == 1:
        return aa[0]
    army = np.asarray(s.armies)
    own = np.asarray(s.ownership[p])
    opp = np.asarray(s.ownership[1 - p])
    rank = []
    for z in aa[1:]:
        _, r, c, d, _ = z
        dr, dc = ((-1, 0), (1, 0), (0, -1), (0, 1))[d]
        y, x = r + dr, c + dc
        moved = int(army[r, c]) - 1
        attack_w = 1 + style % 3
        mass_w = 1 + style // 3
        expand = 55 if (not own[y, x] and not opp[y, x]) else 0
        capture = 220 if opp[y, x] and moved > int(army[y, x]) else (120 if opp[y, x] else 0)
        merge = int(army[y, x]) if own[y, x] else 0
        score = attack_w * capture + mass_w * moved + expand + merge + rng.normal(0, 8)
        rank.append((score, z))
    return max(rank)[1]


def value(s, p: int) -> float:
    winner = int(s.winner)
    if winner >= 0:
        return 100000.0 if winner == p else -100000.0
    own = np.asarray(s.ownership[p])
    opp = np.asarray(s.ownership[1 - p])
    a = np.asarray(s.armies)
    cast = np.asarray(s.castles)
    stacks = np.sort(a[own]) if own.any() else np.array([0])
    return (
        2 * int(a[own].sum() - a[opp].sum())
        + 4 * int(own.sum() - opp.sum())
        + 20 * int((cast & own).sum() - (cast & opp).sum())
        + int(stacks[-1])
        + 0.1 * int(stacks[-3:].sum())
    )


def rollout(step, root, p: int, first, seed: int, horizon: int, style: int) -> float:
    s = clone_state(root)
    rng = np.random.default_rng(seed)
    for turn in range(horizon):
        act = [None, None]
        act[p] = first if turn == 0 else policy(s, p, rng, style)
        act[1 - p] = policy(s, 1 - p, rng, style ^ 3)
        s, _ = step(s, jnp.asarray(act, dtype=jnp.int32))
        if int(s.winner) >= 0:
            break
    return value(s, p)


def _bfs(passable: np.ndarray, start: int) -> np.ndarray:
    h, w = passable.shape
    dist = np.full(h * w, 999, dtype=np.int16)
    if start < 0:
        return dist
    dist[start] = 0
    q = deque([start])
    while q:
        x = q.popleft()
        r, c = divmod(x, w)
        nd = int(dist[x]) + 1
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < h and 0 <= cc < w):
                continue
            y = rr * w + cc
            if passable[rr, cc] and nd < int(dist[y]):
                dist[y] = nd
                q.append(y)
    return dist


def feature_context(s, p: int) -> dict:
    """Build the exact perspective-relative inputs mirrored by C++ V4.1 schema v2."""
    obs = game.get_observation(s, p)
    armies = np.asarray(obs.armies, dtype=np.int32)
    h, w = armies.shape
    fog = np.asarray(obs.fog_cells, dtype=bool)
    structures_fog = np.asarray(obs.structures_in_fog, dtype=bool)
    mountains = np.asarray(obs.mountains, dtype=bool)
    castles = np.asarray(obs.castles, dtype=bool)
    generals = np.asarray(obs.generals, dtype=bool)
    owned = np.asarray(obs.owned_cells, dtype=bool)
    opponent = np.asarray(obs.opponent_cells, dtype=bool)

    types = np.full((h, w), 1, dtype=np.int32)
    types[fog] = 0
    types[structures_fog] = 5
    types[mountains] = 2
    types[castles] = 3
    types[generals] = 4
    owners = np.zeros((h, w), dtype=np.int32)
    owners[owned] = 1
    owners[opponent] = 2

    own_g = np.flatnonzero((types.ravel() == 4) & (owners.ravel() == 1))
    enemy_g = np.flatnonzero((types.ravel() == 4) & (owners.ravel() == 2))
    own_general = int(own_g[0]) if own_g.size else -1
    visible_enemy_general = int(enemy_g[0]) if enemy_g.size else -1
    passable = np.asarray(s.passable, dtype=bool)
    degree = np.zeros(h * w, dtype=np.int8)
    for r in range(h):
        for c in range(w):
            if not passable[r, c]:
                continue
            degree[r * w + c] = sum(
                0 <= r + dr < h and 0 <= c + dc < w and passable[r + dr, c + dc]
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
            )
    return {
        "h": h,
        "w": w,
        "types": types,
        "owners": owners,
        "armies": armies,
        "my_land": int(obs.owned_land_count),
        "my_army": int(obs.owned_army_count),
        "opp_land": int(obs.opponent_land_count),
        "opp_army": int(obs.opponent_army_count),
        "turn": int(obs.timestep),
        "own_castles": int(np.count_nonzero((types == 3) & (owners == 1))),
        "enemy_visible": visible_enemy_general >= 0,
        "contact_visible": bool(np.any(owners == 2)),
        "dist_own": _bfs(passable, own_general),
        "dist_enemy": _bfs(passable, visible_enemy_general),
        "degree": degree,
    }


def features(ctx: dict, z) -> list[int]:
    if z[0]:
        return [mix(1 << 32)]
    _, r, c, d, sp = z
    dr, dc = ((-1, 0), (1, 0), (0, -1), (0, 1))[d]
    y, x = r + dr, c + dc
    h, w = ctx["h"], ctx["w"]
    src = r * w + c
    dst = y * w + x
    a = ctx["armies"]
    owners = ctx["owners"]
    types = ctx["types"]
    source_army = int(a[r, c])
    dest_army = int(a[y, x])
    moved = max(1, (source_army // 2) if sp else (source_army - 1))
    enemy_progress = 0
    if ctx["enemy_visible"]:
        enemy_progress = int(ctx["dist_enemy"][src]) - int(ctx["dist_enemy"][dst])
        enemy_progress = max(-2, min(2, enemy_progress))
    capture_class = 0
    if owners[y, x] == 2 and moved > dest_army:
        capture_class = 2
    elif owners[y, x] == 0 and moved > dest_army:
        capture_class = 1
    merge_bucket = bucket(dest_army + moved) if owners[y, x] == 1 else 0
    own_delta = int(ctx["dist_own"][src]) - int(ctx["dist_own"][dst])
    own_delta = max(-2, min(2, own_delta))

    vals = (
        (1, 0),
        (2, ctx["turn"] // 25),
        (3, min(31, ctx["my_land"] * 8 // max(1, ctx["opp_land"]))),
        (4, min(31, ctx["my_army"] * 8 // max(1, ctx["opp_army"]))),
        (5, min(15, ctx["own_castles"])),
        (6, int(ctx["enemy_visible"])),
        (7, int(ctx["contact_visible"])),
        (8, bucket(source_army)),
        (9, int(types[r, c])),
        (10, int(owners[y, x])),
        (11, bucket(dest_army)),
        (12, int(types[y, x])),
        (13, int(sp)),
        (14, bucket(moved)),
        (15, min(31, int(ctx["dist_own"][src]))),
        (16, min(31, int(ctx["dist_own"][dst]))),
        (17, int(owners[y, x] == 1)),
        (18, int(owners[y, x] == 2)),
        (19, int(owners[y, x] == 0)),
        (20, capture_class),
        (21, merge_bucket),
        (22, enemy_progress),
        (23, bucket(moved) * 8 + enemy_progress + 2),
        (24, int(ctx["degree"][src])),
        (25, int(ctx["degree"][dst])),
        (26, int(r == 0 or c == 0 or r == h - 1 or c == w - 1)),
        (27, int(y == 0 or x == 0 or y == h - 1 or x == w - 1)),
        (28, min(31, moved // 4)),
        (29, bucket(dest_army) * 4 + int(owners[y, x])),
        (30, own_delta),
    )
    return [mix((tag << 32) ^ (int(v) & 0xFFFFFFFF)) for tag, v in vals]


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    with tmp.open("rb") as fh:
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _config(args) -> dict:
    return {
        "pack_version": PACK_VERSION,
        "feature_schema": FEATURE_SCHEMA_VERSION,
        "env_mode": "competition",
        "seed_start": args.seed_start,
        "rollouts": args.rollouts,
        "horizon": args.horizon,
        "states_per_game": args.states_per_game,
        "candidates": args.candidates,
        "hash_bits": args.hash_bits,
    }


def _validate_or_initialize_checkpoint(cp: Path, data: Path, args) -> tuple[dict, dict]:
    cfg = _config(args)
    saved = json.loads(cp.read_text()) if cp.exists() else {}
    old_cfg = saved.get("config")
    if old_cfg is not None and old_cfg != cfg:
        raise SystemExit(f"checkpoint configuration mismatch\nold={old_cfg}\nnew={cfg}")
    stats = {k: int(saved.get(k, 0)) for k in ("games", "states", "raw_rollouts", "usable_pairs")}
    stats["elapsed_seconds"] = float(saved.get("elapsed_seconds", 0.0))
    known_bytes = int(saved.get("data_bytes", 0))
    if data.exists() and saved:
        actual = data.stat().st_size
        if actual < known_bytes:
            raise SystemExit(f"rollout data shorter than checkpoint: {actual} < {known_bytes}")
        if actual > known_bytes:
            # A prior process may have died after appending a game member but before
            # atomically advancing checkpoint.json.  Truncate to the last committed
            # byte so resumption cannot double-count or parse a partial gzip member.
            with data.open("r+b") as fh:
                fh.truncate(known_bytes)
    elif data.exists() and not saved:
        raise SystemExit("rollout data exists without checkpoint; refusing ambiguous resume")
    return stats, cfg


def _append_game_member(data: Path, rows: list[dict]) -> int:
    text = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows)
    member = gzip.compress(text.encode("utf-8"), compresslevel=6)
    with data.open("ab") as out:
        out.write(member)
        out.flush()
        os.fsync(out.fileno())
    return data.stat().st_size


def collect(args, stats: dict, cfg: dict, cp: Path, data: Path) -> dict:
    env = GeneralsEnv(mode="competition")
    step = make_transition(env)
    start = time.monotonic()
    initial_games = stats["games"]
    deadline = None if args.max_wall_minutes <= 0 else start + args.max_wall_minutes * 60.0
    recent_game_seconds = deque(maxlen=5)

    for gi in range(stats["games"], args.max_games):
        if stats["games"] >= args.games and stats["usable_pairs"] >= args.target_pairs:
            break
        now = time.monotonic()
        if deadline is not None and gi > initial_games:
            estimate = max(recent_game_seconds) if recent_game_seconds else 60.0
            if now + max(60.0, estimate * 1.5) >= deadline:
                break
        game_start = time.monotonic()
        seed = args.seed_start + gi
        s = make_board(env, seed)
        rng = np.random.default_rng(seed)
        max_sample_turn = min(500, int(getattr(env, "truncation", 1200) or 1200) - 1)
        low = 20
        high = max(low + 1, max_sample_turn)
        available = np.arange(low, high, dtype=np.int32)
        sample_n = min(args.states_per_game, len(available))
        sample = set(map(int, rng.choice(available, size=sample_n, replace=False)))
        rows: list[dict] = []
        max_play_turn = max(sample) + 1 if sample else 0
        train_p = gi & 1
        for turn in range(max_play_turn):
            if turn in sample and int(s.winner) < 0:
                cs = candidates(s, train_p, args.candidates)
                ctx = feature_context(s, train_p)
                vv = []
                for z in cs:
                    q = [
                        rollout(step, s, train_p, z, seed * 1000 + k, args.horizon, gi % 9)
                        for k in range(args.rollouts)
                    ]
                    vv.append(float(np.mean(q)))
                    stats["raw_rollouts"] += len(q)
                pairs = []
                for i in range(len(cs)):
                    for j in range(i + 1, len(cs)):
                        delta = vv[i] - vv[j]
                        if abs(delta) >= 5:
                            pairs.append((i, j, delta))
                            stats["usable_pairs"] += 1
                rows.append(
                    {
                        "seed": seed,
                        "player": train_p,
                        "turn": turn,
                        "features": [features(ctx, z) for z in cs],
                        "values": vv,
                        "pairs": pairs,
                    }
                )
                stats["states"] += 1
            acts = [policy(s, 0, rng, gi % 9), policy(s, 1, rng, (gi + 4) % 9)]
            s, _ = step(s, jnp.asarray(acts, dtype=jnp.int32))
            if int(s.winner) >= 0:
                break
        data_bytes = _append_game_member(data, rows)
        stats["games"] = gi + 1
        elapsed_this = time.monotonic() - game_start
        recent_game_seconds.append(elapsed_this)
        stats["elapsed_seconds"] += elapsed_this
        checkpoint = stats | {"data_bytes": data_bytes, "config": cfg}
        # A completed game is the atomic work unit.  Checkpoint every game; this is
        # cheap compared with the rollouts and makes cross-run artifacts exact.
        atomic_json(cp, checkpoint)
        if args.progress_every and stats["games"] % args.progress_every == 0:
            print(json.dumps(checkpoint, sort_keys=True), flush=True)
    # Ensure even a zero-game initialization produces a compatible checkpoint.
    if not cp.exists():
        atomic_json(cp, stats | {"data_bytes": data.stat().st_size if data.exists() else 0, "config": cfg})
    return stats


def fit(args, stats: dict, cp: Path, data: Path, cfg: dict) -> dict:
    if not data.exists():
        raise SystemExit("cannot fit: no rollout data")
    size = 1 << args.hash_bits
    w, cov, report = fit_pairs(lambda: read_pairs(data, size), size)
    report["data"] = audit_feature_hashes(data, size)
    report["intervention_rate"] = None
    report["intervention_rate_reason"] = "requires runtime benchmark"
    (args.out / "policy.bin").write_bytes(serialize_policy(w, cov, stats["states"]))
    atomic_json(args.out / "policy-report.json", report)
    result = stats | {
        "data_bytes": data.stat().st_size,
        "config": cfg,
        "nonzero_weights": int(np.count_nonzero(w)),
        "policy_bytes": int((args.out / "policy.bin").stat().st_size),
    }
    atomic_json(cp, result)
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--games", type=int, default=5000, help="minimum completed games")
    p.add_argument("--target-pairs", type=int, default=1_000_000)
    p.add_argument("--max-games", type=int, default=10000, help="hard ceiling if pair gate needs extra games")
    p.add_argument("--seed-start", type=int, default=10000)
    p.add_argument("--rollouts", type=int, default=4)
    p.add_argument("--horizon", type=int, default=50)
    p.add_argument("--states-per-game", type=int, default=10)
    p.add_argument("--candidates", type=int, default=DEFAULT_CANDIDATES)
    p.add_argument("--hash-bits", type=int, choices=(20, 21, 22), default=20)
    p.add_argument("--max-wall-minutes", type=float, default=0.0)
    p.add_argument("--progress-every", type=int, default=10)
    p.add_argument("--collect-only", action="store_true")
    p.add_argument("--fit-only", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cp = args.out / "checkpoint.json"
    data = args.out / "rollouts.jsonl.gz"
    stats, cfg = _validate_or_initialize_checkpoint(cp, data, args)

    if not args.fit_only:
        stats = collect(args, stats, cfg, cp, data)
    if args.collect_only:
        print(cp.read_text(), flush=True)
        return
    result = fit(args, stats, cp, data, cfg)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
