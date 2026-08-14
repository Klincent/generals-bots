#!/usr/bin/env python3
"""Reconstruct the exact pinned V3.4 source and apply only the audited final correction patch."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import tempfile
from pathlib import Path

from prepare_v41_runtime import EXPECTED_INITIAL_SHA256, reconstruct_split_source


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--agent-dir", type=Path, required=True)
    p.add_argument("--patch", type=Path, default=Path("competition/training/v4/v34-final.patch"))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()

    source = reconstruct_split_source(a.agent_dir)
    initial_sha = sha256_bytes(source)
    if initial_sha != EXPECTED_INITIAL_SHA256:
        raise SystemExit(f"unexpected pinned V3.4 source hash {initial_sha}")

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="v34-baseline-", suffix=".cpp", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(source)
    try:
        subprocess.run(["patch", str(tmp_path), "-i", str(a.patch)], check=True)
        final = tmp_path.read_bytes()
        a.output.write_bytes(final)
    finally:
        tmp_path.unlink(missing_ok=True)

    print(f"generated corrected V3.4 {a.output} sha256={sha256_bytes(final)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
