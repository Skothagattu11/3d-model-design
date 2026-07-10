import json
import os
import subprocess
import sys
import pytest
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).parent.parent)

CLI = [sys.executable, "generate_3d.py"]

RING_SPEC = {
    "object_name": "cli_ring",
    "components": [{
        "name": "ring",
        "type": "revolve",
        "profile": [[10.0, 0.0], [20.0, 0.0], [20.0, 5.0], [10.0, 5.0], [10.0, 0.0]],
        "sections": 16,
        "material": {
            "name": "Chrome",
            "base_color": [0.95, 0.95, 0.95, 1.0],
            "metallic": 1.0,
            "roughness": 0.05,
            "alpha_mode": None
        }
    }]
}


def test_validate_only_valid_spec(tmp_path):
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(RING_SPEC))
    result = subprocess.run(
        CLI + ["--spec", str(spec_file), "--validate-only", "--output", str(tmp_path)],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    assert result.returncode == 0
    assert "valid" in result.stdout.lower()


def test_validate_only_invalid_spec(tmp_path):
    spec_file = tmp_path / "bad.json"
    spec_file.write_text(json.dumps({"object_name": "x"}))
    result = subprocess.run(
        CLI + ["--spec", str(spec_file), "--validate-only", "--output", str(tmp_path)],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    assert result.returncode != 0


def test_build_from_spec_file(tmp_path):
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(RING_SPEC))
    result = subprocess.run(
        CLI + ["--spec", str(spec_file), "--output", str(tmp_path)],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    assert result.returncode == 0
    assert os.path.exists(tmp_path / "cli_ring.glb")


def test_build_from_stdin(tmp_path):
    result = subprocess.run(
        CLI + ["--stdin", "--output", str(tmp_path)],
        input=json.dumps(RING_SPEC),
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    assert result.returncode == 0
    assert os.path.exists(tmp_path / "cli_ring.glb")


def test_name_override(tmp_path):
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(RING_SPEC))
    result = subprocess.run(
        CLI + ["--spec", str(spec_file), "--output", str(tmp_path), "--name", "my_ring"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    assert result.returncode == 0
    assert os.path.exists(tmp_path / "my_ring.glb")
