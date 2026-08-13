import struct

import numpy as np
import pytest

from fit_policy_v41 import (HEADER, Pair, confidence_weight, deserialize_policy,
                            fit_pairs, serialize_policy, validation_seed)


def sample_pairs():
    return [
        Pair(seed, (1, 3), (2, 4), delta)
        for seed, delta in ((10, 5.0), (11, 25_000.0), (12, 40.0), (13, 200.0),
                            (14, 10.0), (15, 80.0), (16, 30.0), (17, 120.0))
    ]


def test_seed_split_keeps_games_whole_and_is_deterministic():
    first = {seed: validation_seed(seed, 0.25) for seed in range(100)}
    assert first == {seed: validation_seed(seed, 0.25) for seed in range(100)}
    assert any(first.values()) and not all(first.values())
    assert len({validation_seed(12345, 0.25) for _ in range(20)}) == 1


def test_confidence_is_bounded_for_terminal_delta():
    assert confidence_weight(0.0) == 1.0
    assert confidence_weight(25_000.0) < 4.0
    assert confidence_weight(25_000.0) > confidence_weight(100.0)
    assert confidence_weight(-100.0) == confidence_weight(100.0)


def test_fitter_learns_preference_and_is_byte_deterministic():
    kwargs = dict(hash_size=8, epochs=30, learning_rate=0.08, validation_fraction=0.25)
    w1, c1, report1 = fit_pairs(sample_pairs(), **kwargs)
    w2, c2, report2 = fit_pairs(sample_pairs(), **kwargs)
    assert serialize_policy(w1, c1, 8) == serialize_policy(w2, c2, 8)
    np.testing.assert_array_equal(w1, w2)
    assert report1 == report2
    assert w1[1] + w1[3] > w1[2] + w1[4]
    assert report1["train"]["weighted_accuracy"] == 1.0
    assert report1["split"]["train_seeds"] + report1["split"]["validation_seeds"] == 8


def test_float32_policy_round_trip():
    weights = np.array([0.25, -1.5, 0, 2, 3, 4, 5, 6], dtype=np.float32)
    coverage = np.arange(8, dtype=np.uint32) * 100
    encoded = serialize_policy(weights, coverage, 77)
    actual_weights, actual_coverage, count = deserialize_policy(encoded)
    np.testing.assert_array_equal(actual_weights, weights)
    np.testing.assert_array_equal(actual_coverage, np.minimum(coverage, 255))
    assert count == 77


@pytest.mark.parametrize("mutation", ["checksum", "version", "schema", "truncated", "trailing"])
def test_corrupt_and_incompatible_policy_rejected(mutation):
    encoded = bytearray(serialize_policy(np.zeros(8, np.float32), np.ones(8), 1))
    if mutation == "checksum":
        encoded[-1] ^= 1
    elif mutation == "version":
        struct.pack_into("<I", encoded, 8, 999)
    elif mutation == "schema":
        struct.pack_into("<I", encoded, 32, 999)
    elif mutation == "truncated":
        encoded.pop()
    else:
        encoded.append(0)
    with pytest.raises(ValueError):
        deserialize_policy(bytes(encoded))


def test_runtime_patch_preserves_baseline_fallback_contract():
    from pathlib import Path
    patch = (Path(__file__).parent / "v41-runtime.patch").read_text()
    assert "V4_PACK_VERSION=3" in patch
    assert "std::vector<float> v4_policy_weights_" in patch
    assert "if((!v4_policy_loaded_&&!v4_tactics_loaded_)||cs.empty())return baseline" in patch
    assert "missing %s; V3.4 fallback active" in patch
