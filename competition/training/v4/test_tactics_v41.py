from tactics_v41 import TacticRecord, deserialize_tactics, serialize_tactics, tactic_key


def test_tactic_key_deterministic_and_golden():
    kwargs = dict(dest_owner=2, dest_type=3, source_army=18, dest_army=7,
                  split=False, own_general_distance=4,
                  enemy_general_visible=True, contact_visible=True,
                  source_degree=3, dest_degree=2)
    assert tactic_key(**kwargs) == 7476397078084802427
    assert tactic_key(**kwargs) == tactic_key(**kwargs)
    assert tactic_key(**kwargs) != tactic_key(**{**kwargs, "split": True})


def test_tactics_round_trip_and_deduplicate():
    encoded = serialize_tactics([
        TacticRecord(9, 100, 3),
        TacticRecord(2, -20, 5),
        TacticRecord(9, 40, 1),
    ])
    assert deserialize_tactics(encoded) == [
        TacticRecord(2, -20, 5),
        TacticRecord(9, 85, 4),
    ]


def test_corrupt_tactics_rejected():
    encoded = bytearray(serialize_tactics([TacticRecord(5, 42, 8)]))
    encoded[-1] ^= 1
    try:
        deserialize_tactics(bytes(encoded))
    except ValueError:
        pass
    else:
        raise AssertionError("corrupt tactics pack accepted")
