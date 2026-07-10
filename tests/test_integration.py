import json
import os
import pytest
from engine.build import build

FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "diamond_badge_spec.json"
)


def test_diamond_badge_end_to_end(tmp_path):
    with open(FIXTURE) as f:
        spec = json.load(f)
    out = build(spec, str(tmp_path))
    assert os.path.exists(out)
    assert os.path.getsize(out) > 10_000  # at least 10 KB


def test_diamond_badge_glb_name(tmp_path):
    with open(FIXTURE) as f:
        spec = json.load(f)
    out = build(spec, str(tmp_path))
    assert os.path.basename(out) == "diamond_badge.glb"
