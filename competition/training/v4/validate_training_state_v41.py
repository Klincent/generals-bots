#!/usr/bin/env python3
"""Strictly validate the completed V4.1 rollout artifact before post-training."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED = {
    "games": 5000,
    "states": 47736,
    "raw_rollouts": 1452956,
    "usable_pairs": 1094917,
    "data_bytes": 22648318,
}
EXPECTED_COLLECTION_PACK_VERSION = 2
EXPECTED_FEATURE_SCHEMA = 2
EXPECTED_ENV_MODE = "competition"


def validate_state(state_dir: Path) -> dict:
    checkpoint_path = state_dir / "checkpoint.json"
    rollouts_path = state_dir / "rollouts.jsonl.gz"
    if not checkpoint_path.is_file():
        raise ValueError("missing checkpoint.json")
    if not rollouts_path.is_file():
        raise ValueError("missing rollouts.jsonl.gz")

    checkpoint = json.loads(checkpoint_path.read_text())
    config = checkpoint.get("config")
    if not isinstance(config, dict):
        raise ValueError("checkpoint config missing or invalid")
    if config.get("pack_version") != EXPECTED_COLLECTION_PACK_VERSION:
        raise ValueError(
            f"unexpected collection pack_version {config.get('pack_version')} != "
            f"{EXPECTED_COLLECTION_PACK_VERSION}"
        )
    if config.get("feature_schema") != EXPECTED_FEATURE_SCHEMA:
        raise ValueError(
            f"unexpected feature_schema {config.get('feature_schema')} != {EXPECTED_FEATURE_SCHEMA}"
        )
    if config.get("env_mode") != EXPECTED_ENV_MODE:
        raise ValueError(f"unexpected env_mode {config.get('env_mode')!r}")

    for key, expected in EXPECTED.items():
        actual = checkpoint.get(key)
        if actual != expected:
            raise ValueError(f"unexpected checkpoint {key}: {actual!r} != {expected}")

    actual_bytes = rollouts_path.stat().st_size
    if actual_bytes != EXPECTED["data_bytes"]:
        raise ValueError(
            f"rollout byte count mismatch: {actual_bytes} != {EXPECTED['data_bytes']}"
        )

    return {
        "accepted": True,
        "checkpoint": {key: checkpoint[key] for key in EXPECTED},
        "collection_pack_version": config["pack_version"],
        "feature_schema": config["feature_schema"],
        "env_mode": config["env_mode"],
        "rollouts_path": str(rollouts_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = validate_state(args.state_dir)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
