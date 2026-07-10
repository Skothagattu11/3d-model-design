import trimesh
from engine.primitives import revolve, extrude, convex_hull_gem


RING_PROFILE = [
    [10.0, 0.0], [20.0, 0.0], [20.0, 5.0], [10.0, 5.0], [10.0, 0.0]
]

SQUARE_POLYGON = [
    [0.0, 0.0], [30.0, 0.0], [30.0, 20.0], [0.0, 20.0]
]

GEM_POINTS = [
    [0.0, 0.0, 0.0],
    [4.0, 0.0, 5.0], [0.0, 4.0, 5.0], [-4.0, 0.0, 5.0], [0.0, -4.0, 5.0],
    [0.0, 0.0, 8.0]
]


def test_revolve_returns_trimesh():
    m = revolve(RING_PROFILE, sections=32)
    assert isinstance(m, trimesh.Trimesh)


def test_revolve_has_vertices():
    m = revolve(RING_PROFILE, sections=32)
    assert len(m.vertices) > 0
    assert len(m.faces) > 0


def test_revolve_sections_affects_resolution():
    low = revolve(RING_PROFILE, sections=16)
    high = revolve(RING_PROFILE, sections=64)
    assert len(high.vertices) > len(low.vertices)


def test_extrude_returns_trimesh():
    m = extrude(SQUARE_POLYGON, height=3.0)
    assert isinstance(m, trimesh.Trimesh)


def test_extrude_has_faces():
    m = extrude(SQUARE_POLYGON, height=3.0)
    assert len(m.faces) > 0


def test_convex_hull_gem_returns_trimesh():
    m = convex_hull_gem(GEM_POINTS)
    assert isinstance(m, trimesh.Trimesh)


def test_convex_hull_gem_has_faces():
    m = convex_hull_gem(GEM_POINTS)
    assert len(m.faces) > 0


def test_convex_hull_gem_unmerge_true_gives_flat_shading():
    merged = convex_hull_gem(GEM_POINTS, unmerge=False)
    unmerged = convex_hull_gem(GEM_POINTS, unmerge=True)
    assert len(unmerged.vertices) >= len(merged.vertices)
