import numpy as np
import trimesh
from shapely.geometry import Polygon


def revolve(profile: list, sections: int = 256) -> trimesh.Trimesh:
    pts = np.array(profile, dtype=np.float64)
    m = trimesh.creation.revolve(pts, sections=sections)
    m.merge_vertices()
    return m


def extrude(polygon: list, height: float) -> trimesh.Trimesh:
    poly = Polygon(polygon)
    m = trimesh.creation.extrude_polygon(poly, height)
    m.merge_vertices()
    return m


def convex_hull_gem(points: list, unmerge: bool = True) -> trimesh.Trimesh:
    pts = np.array(points, dtype=np.float64)
    hull = trimesh.convex.convex_hull(pts)
    if unmerge:
        hull.unmerge_vertices()
    return hull
