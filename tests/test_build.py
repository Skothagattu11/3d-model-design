import os
import json
import tempfile
import pytest
from engine.build import build

RING_SPEC = {
    "object_name": "test_ring",
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

MULTI_SPEC = {
    "object_name": "multi",
    "components": [
        {
            "name": "ring",
            "type": "revolve",
            "profile": [[10.0, 0.0], [20.0, 0.0], [20.0, 5.0], [10.0, 5.0], [10.0, 0.0]],
            "sections": 16,
            "material": {
                "name": "BrushedGold",
                "base_color": [0.83, 0.66, 0.24, 1.0],
                "metallic": 1.0,
                "roughness": 0.42,
                "alpha_mode": None
            }
        },
        {
            "name": "gem",
            "type": "convex_hull_gem",
            "points": [
                [0.0, 0.0, 5.0], [3.0, 0.0, 7.5], [0.0, 3.0, 7.5],
                [-3.0, 0.0, 7.5], [0.0, -3.0, 7.5], [0.0, 0.0, 10.0]
            ],
            "material": {
                "name": "Diamond",
                "base_color": [1.0, 1.0, 1.0, 0.92],
                "metallic": 0.1,
                "roughness": 0.02,
                "alpha_mode": "BLEND"
            }
        }
    ]
}


def test_build_creates_glb(tmp_path):
    out = build(RING_SPEC, str(tmp_path))
    assert os.path.exists(out)
    assert out.endswith(".glb")


def test_build_returns_correct_path(tmp_path):
    out = build(RING_SPEC, str(tmp_path))
    assert os.path.basename(out) == "test_ring.glb"


def test_build_name_override(tmp_path):
    out = build(RING_SPEC, str(tmp_path), name="my_ring")
    assert os.path.basename(out) == "my_ring.glb"


def test_build_creates_output_dir(tmp_path):
    new_dir = str(tmp_path / "new_subdir")
    out = build(RING_SPEC, new_dir)
    assert os.path.exists(new_dir)
    assert os.path.exists(out)


def test_build_multi_component(tmp_path):
    out = build(MULTI_SPEC, str(tmp_path))
    assert os.path.exists(out)
    assert os.path.getsize(out) > 1000  # non-trivial GLB


def test_build_invalid_spec_raises(tmp_path):
    bad = {"object_name": "x"}  # missing components
    with pytest.raises(ValueError, match="components"):
        build(bad, str(tmp_path))
