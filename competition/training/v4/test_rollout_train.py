import jax.numpy as jnp
import numpy as np
from generals import GeneralsEnv
from matchup import make_board, make_transition
from rollout_train import clone_state


def test_clone_replay_identical_on_competition_ruleset():
    env = GeneralsEnv(mode="competition")
    step = make_transition(env)
    a = make_board(env, 12345)
    b = clone_state(a)
    actions = jnp.array([[1, 0, 0, 0, 0], [1, 0, 0, 0, 0]], dtype=jnp.int32)
    for _ in range(12):
        a, _ = step(a, actions)
        b, _ = step(b, actions)
    for x, y in zip(a, b):
        np.testing.assert_array_equal(np.asarray(x), np.asarray(y))
