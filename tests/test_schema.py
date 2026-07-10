import pytest
from engine.schema import validate

MINIMAL_REVOLVE = {
    "object_name": "test_ring",
    "components": [{
        "name": "ring",
        "type": "revolve",
        "profile": [[10.0, 0.0], [20.0, 0.0], [20.0, 5.0], [10.0, 5.0], [10.0, 0.0]],
        "sections": 64,
        "material": {
            "name": "Chrome",
            "base_color": [0.9, 0.9, 0.9, 1.0],
            "metallic": 1.0,
            "roughness": 0.1,
            "alpha_mode": None
        }
    }]
}

MINIMAL_EXTRUDE = {
    "object_name": "test_plaque",
    "components": [{
        "name": "plaque",
        "type": "extrude",
        "profile": [[0.0, 0.0], [30.0, 0.0], [30.0, 20.0], [0.0, 20.0]],
        "height": 3.0,
        "material": {
            "name": "BlackMatte",
            "base_color": [0.05, 0.05, 0.05, 1.0],
            "metallic": 0.0,
            "roughness": 0.9,
            "alpha_mode": None
        }
    }]
}

MINIMAL_GEM = {
    "object_name": "test_gem",
    "components": [{
        "name": "gem",
        "type": "convex_hull_gem",
        "points": [
            [0.0, 0.0, 0.0], [4.0, 0.0, 5.0],
            [0.0, 4.0, 5.0], [-4.0, 0.0, 5.0],
            [0.0, -4.0, 5.0], [0.0, 0.0, 8.0]
        ],
        "material": {
            "name": "Diamond",
            "base_color": [1.0, 1.0, 1.0, 0.92],
            "metallic": 0.1,
            "roughness": 0.02,
            "alpha_mode": "BLEND"
        }
    }]
}


def test_valid_revolve():
    validate(MINIMAL_REVOLVE)  # must not raise


def test_valid_extrude():
    validate(MINIMAL_EXTRUDE)  # must not raise


def test_valid_gem():
    validate(MINIMAL_GEM)  # must not raise


def test_missing_object_name():
    bad = {**MINIMAL_REVOLVE}
    del bad["object_name"]
    with pytest.raises(ValueError, match="object_name"):
        validate(bad)


def test_missing_components():
    bad = {**MINIMAL_REVOLVE}
    del bad["components"]
    with pytest.raises(ValueError, match="components"):
        validate(bad)


def test_unknown_type():
    bad = {
        "object_name": "x",
        "components": [{**MINIMAL_REVOLVE["components"][0], "type": "sphere"}]
    }
    with pytest.raises(ValueError, match="unknown type"):
        validate(bad)


def test_negative_radius():
    bad_profile = [[-1.0, 0.0], [20.0, 0.0], [20.0, 5.0], [-1.0, 5.0], [-1.0, 0.0]]
    bad = {
        "object_name": "x",
        "components": [{**MINIMAL_REVOLVE["components"][0], "profile": bad_profile}]
    }
    with pytest.raises(ValueError, match="r must be"):
        validate(bad)


def test_extrude_missing_height():
    bad = {
        "object_name": "x",
        "components": [{**MINIMAL_EXTRUDE["components"][0]}]
    }
    del bad["components"][0]["height"]
    with pytest.raises(ValueError, match="height"):
        validate(bad)


def test_gem_too_few_points():
    bad = {
        "object_name": "x",
        "components": [{**MINIMAL_GEM["components"][0], "points": [[0, 0, 0], [1, 0, 0], [0, 1, 0]]}]
    }
    with pytest.raises(ValueError, match="4 points"):
        validate(bad)


def test_missing_material_field():
    bad_mat = {**MINIMAL_REVOLVE["components"][0]["material"]}
    del bad_mat["metallic"]
    bad = {
        "object_name": "x",
        "components": [{**MINIMAL_REVOLVE["components"][0], "material": bad_mat}]
    }
    with pytest.raises(ValueError, match="metallic"):
        validate(bad)


def test_base_color_wrong_length():
    bad_mat = {**MINIMAL_REVOLVE["components"][0]["material"], "base_color": [1.0, 1.0, 1.0]}
    bad = {
        "object_name": "x",
        "components": [{**MINIMAL_REVOLVE["components"][0], "material": bad_mat}]
    }
    with pytest.raises(ValueError, match="base_color"):
        validate(bad)
