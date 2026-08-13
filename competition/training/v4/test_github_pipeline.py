import json
from pathlib import Path

from rollout_train import FEATURE_SCHEMA_VERSION, PACK_VERSION
from run_github_chunk import completed


def test_completed_handles_new_and_resumed_state(tmp_path: Path):
    checkpoint = tmp_path / "checkpoint.json"
    assert completed(checkpoint) == 0
    checkpoint.write_text(json.dumps({"games": 123}))
    assert completed(checkpoint) == 123


def test_python_pack_schema_matches_runtime_patch():
    root = Path(__file__).resolve().parents[3]
    patch = root / "competition" / "training" / "v4" / "v41-runtime.patch"
    text = patch.read_text()
    assert PACK_VERSION == 3
    assert FEATURE_SCHEMA_VERSION == 2
    assert "V4_PACK_VERSION=3" in text
    assert "V4_FEATURE_SCHEMA=2" in text
    assert "V4.1 feature schema v2" in text
