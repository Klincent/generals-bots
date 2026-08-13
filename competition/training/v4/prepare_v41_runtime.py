#!/usr/bin/env python3
"""Reconstruct the corrected V4.1 C++ runtime from the repository's split V3.4 source.

The juraj-v3.4 branch stores the original V3.4 main.cpp as exact textual include
chunks.  To avoid transporting a 150+ KiB monolithic file through the GitHub API,
cloud training reconstructs that source, applies the audited V3.4-final patch and
then the small V4.1 runtime patch, and emits one monolithic main.v41.cpp.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

EXPECTED_INITIAL_SHA256 = "19a8a2107d16229a4246e6da7a47d1052a56a3aac52d2c3fc6a8363d6986ed1c"
EXPECTED_FINAL_SHA256 = "666f7ed64f30f71bb0b593f450ffba5d89c9404952406b6e5a92d8ca00a1d478"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reconstruct_split_source(agent_dir: Path) -> bytes:
    wrapper = (agent_dir / "main.cpp").read_text()
    names = re.findall(r'^#include\s+"(v34_part\d+\.inc)"\s*$', wrapper, flags=re.M)
    if not names:
        raise SystemExit("juraj_cpp/main.cpp does not contain V3.4 split include chunks")
    return b"".join((agent_dir / name).read_bytes() for name in names)


def apply_patch(target: Path, patch_file: Path) -> None:
    subprocess.run(["patch", str(target), "-i", str(patch_file)], check=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--agent-dir", type=Path, default=Path("competition/agents/juraj_cpp"))
    p.add_argument("--patch-dir", type=Path, default=Path("competition/training/v4"))
    p.add_argument("--output", type=Path, default=Path("competition/agents/juraj_cpp/main.v41.cpp"))
    args = p.parse_args()

    initial = reconstruct_split_source(args.agent_dir)
    initial_sha = sha256_bytes(initial)
    if initial_sha != EXPECTED_INITIAL_SHA256:
        raise SystemExit(
            "unexpected split V3.4 source hash: "
            f"{initial_sha} != {EXPECTED_INITIAL_SHA256}; refusing to patch unknown source"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="v41-runtime-", suffix=".cpp", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(initial)
    try:
        apply_patch(tmp_path, args.patch_dir / "v34-final.patch")
        apply_patch(tmp_path, args.patch_dir / "v41-runtime.patch")
        final = tmp_path.read_bytes()
        final_sha = sha256_bytes(final)
        if final_sha != EXPECTED_FINAL_SHA256:
            raise SystemExit(
                f"generated V4.1 source hash {final_sha} != expected {EXPECTED_FINAL_SHA256}"
            )
        args.output.write_bytes(final)
    finally:
        tmp_path.unlink(missing_ok=True)

    print(f"generated {args.output} sha256={EXPECTED_FINAL_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
