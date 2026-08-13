#!/usr/bin/env python3
"""Reconstruct the corrected V4.1 C++ runtime from the repository's split V3.4 source."""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

EXPECTED_INITIAL_SHA256 = "19a8a2107d16229a4246e6da7a47d1052a56a3aac52d2c3fc6a8363d6986ed1c"
EXPECTED_PHASE1_SHA256 = "666f7ed64f30f71bb0b593f450ffba5d89c9404952406b6e5a92d8ca00a1d478"
# Filled after CI proves the deterministic Phase 2 transform compiles.
EXPECTED_PHASE2_SHA256: str | None = None

PHASE2_TACTIC_KEY = '''    uint64_t v4_tactic_key(const Observation&o,const Action&a)const{if(a.kind!=0)return 0;int x=cell(a.row,a.col),y=neighbor(x,a.dir);if(x<0||y<0||x>=n_||y>=n_)return 0;int gdist=std::min(31,dist_[cell_id_[y]][cell_id_[general_]]);bool contact=false,enemy_visible=false;for(int i=0;i<n_;++i)if(o.owner[i]==2){contact=true;if(o.type[i]==4)enemy_visible=true;}uint64_t k=(uint64_t(o.owner[y])&3u)|((uint64_t(o.type[y])&7u)<<2)|((uint64_t(v4_bucket(o.army[x]))&7u)<<5)|((uint64_t(v4_bucket(o.army[y]))&7u)<<8)|(uint64_t(a.split)<<11)|((uint64_t(gdist)&31u)<<12)|(uint64_t(enemy_visible)<<17)|(uint64_t(contact)<<18)|((uint64_t(degree_[x])&7u)<<19)|((uint64_t(degree_[y])&7u)<<22)|(uint64_t(1)<<56);return v4_mix(k);}
'''


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


def apply_phase2_transform(source: bytes) -> bytes:
    text = source.decode("utf-8")
    pattern = r"^    uint64_t v4_tactic_key\(const Observation&o,const Action&a\)const\{.*\}\n"
    updated, count = re.subn(pattern, PHASE2_TACTIC_KEY, text, count=1, flags=re.M)
    if count != 1:
        raise SystemExit(f"expected exactly one Phase 1 v4_tactic_key, found {count}")
    return updated.encode("utf-8")


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
        phase1 = tmp_path.read_bytes()
        phase1_sha = sha256_bytes(phase1)
        if phase1_sha != EXPECTED_PHASE1_SHA256:
            raise SystemExit(
                f"generated Phase 1 V4.1 source hash {phase1_sha} != expected {EXPECTED_PHASE1_SHA256}"
            )

        final = apply_phase2_transform(phase1)
        final_sha = sha256_bytes(final)
        if EXPECTED_PHASE2_SHA256 is not None and final_sha != EXPECTED_PHASE2_SHA256:
            raise SystemExit(
                f"generated Phase 2 V4.1 source hash {final_sha} != expected {EXPECTED_PHASE2_SHA256}"
            )
        args.output.write_bytes(final)
    finally:
        tmp_path.unlink(missing_ok=True)

    print(f"generated {args.output} sha256={final_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
