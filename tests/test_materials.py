import trimesh
import pytest
from engine.materials import apply, PRESETS


def _sphere():
    return trimesh.creation.icosphere(radius=5.0)


def test_presets_has_expected_keys():
    for key in ("BrushedGold", "PolishedSteel", "Diamond", "Chrome",
                "MatteSilver", "BlackMatte", "RoseGold", "Platinum"):
        assert key in PRESETS, f"Missing preset: {key}"


def test_apply_sets_visual():
    mesh = _sphere()
    spec = {
        "name": "BrushedGold",
        "base_color": [0.83, 0.66, 0.24, 1.0],
        "metallic": 1.0,
        "roughness": 0.42,
        "alpha_mode": None
    }
    result = apply(mesh, spec)
    assert result.visual is not None


def test_apply_returns_same_mesh():
    mesh = _sphere()
    spec = {
        "name": "Chrome",
        "base_color": [0.95, 0.95, 0.95, 1.0],
        "metallic": 1.0,
        "roughness": 0.05,
        "alpha_mode": None
    }
    result = apply(mesh, spec)
    assert result is mesh


def test_apply_with_blend_alpha():
    mesh = _sphere()
    spec = {
        "name": "Diamond",
        "base_color": [1.0, 1.0, 1.0, 0.92],
        "metallic": 0.1,
        "roughness": 0.02,
        "alpha_mode": "BLEND"
    }
    result = apply(mesh, spec)
    assert result.visual is not None
