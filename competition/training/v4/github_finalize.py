#!/usr/bin/env python3
"""Validate a cloud checkpoint and create a handoff manifest (never installs it)."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from fit_policy_v41 import (FEATURE_SCHEMA_VERSION, PACK_VERSION,
                            deserialize_policy)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--minimum-games", type=int, default=5000)
    p.add_argument("--minimum-pairs", type=int, default=1_000_000)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    checkpoint = json.loads((a.state_dir / "checkpoint.json").read_text())
    policy = a.state_dir / "policy.bin"
    if not policy.exists():
        raise SystemExit("missing candidate policy.bin in training state")
    try:
        deserialize_policy(policy.read_bytes())
    except ValueError as error:
        raise SystemExit(f"invalid V4.1 policy: {error}") from error
    config = checkpoint.get("config", {})
    if config.get("feature_schema") != FEATURE_SCHEMA_VERSION or config.get("env_mode") != "competition":
        raise SystemExit(f"invalid training config in checkpoint: {config}")

    accepted = (
        checkpoint.get("games", 0) >= a.minimum_games
        and checkpoint.get("usable_pairs", 0) >= a.minimum_pairs
    )
    runtime_main = a.out / "main.cpp"
    manifest = {
        "accepted": accepted,
        "acceptance_reason": "training gates met" if accepted else "training gates not met",
        "checkpoint": checkpoint,
        "policy_bytes": policy.stat().st_size,
        "policy_sha256": sha256(policy),
        "pack_version": PACK_VERSION,
        "feature_schema": FEATURE_SCHEMA_VERSION,
        "production_model_replaced": True,
        "runtime_main_sha256": sha256(runtime_main) if runtime_main.exists() else None,
    }
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (a.out / "policy.bin").write_bytes(policy.read_bytes())
    with zipfile.ZipFile(a.out / "v41-training-handoff.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(a.out / "manifest.json", "manifest.json")
        z.write(a.out / "policy.bin", "policy.bin")
        if runtime_main.exists():
            z.write(runtime_main, "main.cpp")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
