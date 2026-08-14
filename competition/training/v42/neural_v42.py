#!/usr/bin/env python3
"""Pure-JAX V4.2 policy/value network and action codec."""
from __future__ import annotations

from typing import Any

import jax
import jax.numpy as jnp
import numpy as np

BOARD = 21
CELL_ACTIONS = 9  # 4 dirs x {full, half}, then build
PASS_INDEX = BOARD * BOARD * CELL_ACTIONS
ACTION_COUNT = PASS_INDEX + 1
TYPE_COUNT = 6
OWNER_COUNT = 3
GLOBAL_COUNT = 7
INPUT_CHANNELS = TYPE_COUNT + OWNER_COUNT + 4 + GLOBAL_COUNT
DEFAULT_WIDTH = 32
DEFAULT_BLOCKS = 4


def action_to_index(action) -> int:
    """Encode protocol action [kind,row,col,dir,split] into 0..3969."""
    a = [int(x) for x in action]
    kind, r, c, direction, split = a
    if kind == 1:
        return PASS_INDEX
    if not (0 <= r < BOARD and 0 <= c < BOARD):
        raise ValueError(f"cell out of range: {a}")
    if kind == 2:
        channel = 8
    elif kind == 0:
        if not (0 <= direction < 4 and split in (0, 1)):
            raise ValueError(f"bad move action: {a}")
        channel = direction * 2 + split
    else:
        raise ValueError(f"bad action kind: {a}")
    return (r * BOARD + c) * CELL_ACTIONS + channel


def index_to_action(index: int) -> tuple[int, int, int, int, int]:
    index = int(index)
    if index == PASS_INDEX:
        return (1, 0, 0, 0, 0)
    if not 0 <= index < PASS_INDEX:
        raise ValueError(index)
    cell, channel = divmod(index, CELL_ACTIONS)
    r, c = divmod(cell, BOARD)
    if channel == 8:
        return (2, r, c, 0, 0)
    direction, split = divmod(channel, 2)
    return (0, r, c, direction, split)


def pad_observation(obs) -> dict[str, np.ndarray]:
    """Convert one perspective-relative engine Observation to 21x21 arrays."""
    armies = np.asarray(obs.armies, dtype=np.int32)
    h, w = armies.shape
    if not (1 <= h <= BOARD and 1 <= w <= BOARD):
        raise ValueError((h, w))

    types = np.full((BOARD, BOARD), 2, dtype=np.uint8)  # padded cells = mountains
    owners = np.zeros((BOARD, BOARD), dtype=np.uint8)
    aa = np.zeros((BOARD, BOARD), dtype=np.int32)
    valid = np.zeros((BOARD, BOARD), dtype=np.uint8)

    fog = np.asarray(obs.fog_cells, dtype=bool)
    structures_fog = np.asarray(obs.structures_in_fog, dtype=bool)
    mountains = np.asarray(obs.mountains, dtype=bool)
    castles = np.asarray(obs.castles, dtype=bool)
    generals = np.asarray(obs.generals, dtype=bool)
    t = np.full((h, w), 1, dtype=np.uint8)
    t[fog] = 0
    t[structures_fog] = 5
    t[mountains] = 2
    t[castles] = 3
    t[generals] = 4

    owned = np.asarray(obs.owned_cells, dtype=bool)
    opponent = np.asarray(obs.opponent_cells, dtype=bool)
    o = np.zeros((h, w), dtype=np.uint8)
    o[owned] = 1
    o[opponent] = 2

    types[:h, :w] = t
    owners[:h, :w] = o
    aa[:h, :w] = armies
    valid[:h, :w] = 1
    globals_ = np.asarray([
        int(obs.timestep),
        int(obs.owned_land_count),
        int(obs.owned_army_count),
        int(obs.opponent_land_count),
        int(obs.opponent_army_count),
    ], dtype=np.int32)
    return {"types": types, "owners": owners, "armies": aa, "valid": valid, "globals": globals_}


def encode_inputs(batch: dict[str, jnp.ndarray]) -> jnp.ndarray:
    types = jnp.asarray(batch["types"], dtype=jnp.int32)
    owners = jnp.asarray(batch["owners"], dtype=jnp.int32)
    armies = jnp.asarray(batch["armies"], dtype=jnp.float32)
    valid = jnp.asarray(batch["valid"], dtype=jnp.float32)
    g = jnp.asarray(batch["globals"], dtype=jnp.float32)
    if types.ndim == 2:
        types = types[None]
        owners = owners[None]
        armies = armies[None]
        valid = valid[None]
        g = g[None]

    type_oh = jax.nn.one_hot(types, TYPE_COUNT, dtype=jnp.float32)
    owner_oh = jax.nn.one_hot(owners, OWNER_COUNT, dtype=jnp.float32)
    army_log = jnp.log1p(jnp.clip(armies, 0, 100000.0)) / jnp.log(100001.0)
    army_log = army_log[..., None]
    own_army = army_log * (owners == 1)[..., None]
    opp_army = army_log * (owners == 2)[..., None]
    valid_ch = valid[..., None]

    area = jnp.maximum(valid.sum(axis=(1, 2)), 1.0)
    turn = jnp.clip(g[:, 0] / 1200.0, 0.0, 1.5)
    my_land = g[:, 1] / area
    my_army = jnp.log1p(jnp.maximum(g[:, 2], 0.0)) / jnp.log(100001.0)
    opp_land = g[:, 3] / area
    opp_army = jnp.log1p(jnp.maximum(g[:, 4], 0.0)) / jnp.log(100001.0)
    land_balance = (g[:, 1] - g[:, 3]) / jnp.maximum(g[:, 1] + g[:, 3], 1.0)
    army_balance = (g[:, 2] - g[:, 4]) / jnp.maximum(g[:, 2] + g[:, 4], 1.0)
    global_vec = jnp.stack((turn, my_land, opp_land, my_army, opp_army,
                            land_balance, army_balance), axis=-1)
    global_map = jnp.broadcast_to(global_vec[:, None, None, :],
                                  (types.shape[0], BOARD, BOARD, GLOBAL_COUNT))
    x = jnp.concatenate((type_oh, owner_oh, army_log, own_army, opp_army,
                         valid_ch, global_map), axis=-1)
    return x * valid_ch


def _castle_kernel() -> jnp.ndarray:
    radius = 6
    k = np.zeros((2 * radius + 1, 2 * radius + 1, 1, 1), dtype=np.float32)
    for i in range(-radius, radius + 1):
        for j in range(-radius, radius + 1):
            k[i + radius, j + radius, 0, 0] = max(0, 14 - 2 * (abs(i) + abs(j)))
    return jnp.asarray(k)


_CASTLE_KERNEL = _castle_kernel()


def legal_action_mask(batch: dict[str, jnp.ndarray]) -> jnp.ndarray:
    """Return [B,3970] legal/known-legal mask from the observation.

    Fog targets remain potentially movable because their hidden terrain is unknown;
    visible mountains and padded cells are masked. Builds are exactly computable
    from own visible structures and armies under the competition modifier.
    """
    types = jnp.asarray(batch["types"], dtype=jnp.int32)
    owners = jnp.asarray(batch["owners"], dtype=jnp.int32)
    armies = jnp.asarray(batch["armies"], dtype=jnp.float32)
    valid = jnp.asarray(batch["valid"], dtype=jnp.bool_)
    if types.ndim == 2:
        types, owners, armies, valid = (x[None] for x in (types, owners, armies, valid))

    src = valid & (owners == 1) & (armies > 1)
    target = valid & (types != 2)
    false_row = ((0, 0), (1, 0), (0, 0))
    up = jnp.pad(target[:, :-1, :], false_row)
    down = jnp.pad(target[:, 1:, :], ((0, 0), (0, 1), (0, 0)))
    left = jnp.pad(target[:, :, :-1], ((0, 0), (0, 0), (1, 0)))
    right = jnp.pad(target[:, :, 1:], ((0, 0), (0, 0), (0, 1)))
    dirs = (up, down, left, right)
    moves = jnp.stack([src & d for d in dirs for _split in (0, 1)], axis=-1)

    structures = ((owners == 1) & ((types == 3) | (types == 4))).astype(jnp.float32)
    surcharge = jax.lax.conv_general_dilated(
        structures[..., None], _CASTLE_KERNEL, (1, 1), "SAME",
        dimension_numbers=("NHWC", "HWIO", "NHWC"),
    )[..., 0]
    build_cost = 35.0 + surcharge
    build = valid & (owners == 1) & (types == 1) & (armies >= build_cost)
    cell = jnp.concatenate((moves, build[..., None]), axis=-1).reshape(types.shape[0], -1)
    return jnp.concatenate((cell, jnp.ones((types.shape[0], 1), dtype=jnp.bool_)), axis=-1)


def _he_init(key, shape) -> jnp.ndarray:
    fan_in = np.prod(shape[:-1])
    return jax.random.normal(key, shape, dtype=jnp.float32) * np.sqrt(2.0 / fan_in)


def init_params(key: jax.Array, width: int = DEFAULT_WIDTH,
                blocks: int = DEFAULT_BLOCKS) -> dict[str, Any]:
    keys = iter(jax.random.split(key, 4 + 4 * blocks))
    p: dict[str, Any] = {
        "stem_w": _he_init(next(keys), (3, 3, INPUT_CHANNELS, width)),
        "stem_b": jnp.zeros((width,), dtype=jnp.float32),
        "blocks": [],
    }
    for _ in range(blocks):
        p["blocks"].append({
            "w1": _he_init(next(keys), (3, 3, width, width)),
            "b1": jnp.zeros((width,), dtype=jnp.float32),
            "w2": _he_init(next(keys), (3, 3, width, width)),
            "b2": jnp.zeros((width,), dtype=jnp.float32),
        })
    p.update({
        "policy_w": _he_init(next(keys), (1, 1, width, CELL_ACTIONS)),
        "policy_b": jnp.zeros((CELL_ACTIONS,), dtype=jnp.float32),
        "pass_w": _he_init(next(keys), (width, 1)),
        "pass_b": jnp.zeros((1,), dtype=jnp.float32),
        "value_w1": _he_init(next(keys), (width, 64)),
        "value_b1": jnp.zeros((64,), dtype=jnp.float32),
        "value_w2": _he_init(next(keys), (64, 1)),
        "value_b2": jnp.zeros((1,), dtype=jnp.float32),
    })
    return p


def _conv(x, w, b):
    y = jax.lax.conv_general_dilated(
        x, w, (1, 1), "SAME", dimension_numbers=("NHWC", "HWIO", "NHWC")
    )
    return y + b


def policy_value(params: dict[str, Any], batch: dict[str, jnp.ndarray]) -> tuple[jnp.ndarray, jnp.ndarray]:
    x = encode_inputs(batch)
    valid = jnp.asarray(batch["valid"], dtype=jnp.float32)
    if valid.ndim == 2:
        valid = valid[None]
    vm = valid[..., None]
    x = jax.nn.relu(_conv(x, params["stem_w"], params["stem_b"])) * vm
    for block in params["blocks"]:
        y = jax.nn.relu(_conv(x, block["w1"], block["b1"])) * vm
        y = _conv(y, block["w2"], block["b2"]) * vm
        x = jax.nn.relu(x + y) * vm

    cell_logits = _conv(x, params["policy_w"], params["policy_b"]).reshape(x.shape[0], -1)
    denom = jnp.maximum(vm.sum(axis=(1, 2)), 1.0)
    pooled = (x * vm).sum(axis=(1, 2)) / denom
    pass_logit = pooled @ params["pass_w"] + params["pass_b"]
    logits = jnp.concatenate((cell_logits, pass_logit), axis=-1)

    v = jax.nn.relu(pooled @ params["value_w1"] + params["value_b1"])
    value = jnp.tanh(v @ params["value_w2"] + params["value_b2"])[:, 0]
    return logits, value


def masked_logits(params: dict[str, Any], batch: dict[str, jnp.ndarray]) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
    logits, value = policy_value(params, batch)
    legal = legal_action_mask(batch)
    return jnp.where(legal, logits, -1.0e9), value, legal


def count_params(params: dict[str, Any]) -> int:
    return int(sum(np.prod(x.shape) for x in jax.tree_util.tree_leaves(params)))
