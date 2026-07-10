"""
spatial_disc.py — Seamless spatial-depth badge GLB.

Builds a single continuous displaced mesh where the badge geometry recedes
INWARD — the frame/rim sits at the front face (Z=0) and the inner scene
(figure, mountains, stars) carves deeper into the badge.

Looking face-on: a perfect flat badge.
Rotating: you see the scene depth going into the badge like a carved medallion.

No separate planes. No visible layers. One seamless surface.

Usage:
    python spatial_disc.py --input badge.png --output badge_spatial.glb
    python spatial_disc.py --input badge.png --output badge_spatial.glb \\
        --depth-scale 6 --grid 384 --thickness 4
"""

import argparse
import os
import numpy as np
from PIL import Image, ImageFilter
import trimesh
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial

from depth_render import make_depth_map, smooth_depth, contrast_depth


def get_depth(rgb: np.ndarray) -> np.ndarray:
    d = make_depth_map(rgb)
    d = contrast_depth(d, gamma=0.85, levels=2.0)
    d = smooth_depth(d, radius=5)
    return d


def build_mesh(
    rgb: np.ndarray,
    depth: np.ndarray,
    badge_radius: float = 50.,
    depth_scale: float = 6.,
    grid: int = 384,
) -> trimesh.Trimesh:
    """
    NxN vertex grid. Each vertex Z = -(1 - depth) * depth_scale so that:
      depth=1 (gold frame, bright highlights) -> Z = 0  (front face)
      depth=0 (dark stars, background)        -> Z = -depth_scale (recessed inward)

    Pixels outside the badge circle are clamped to Z=0 (flat rim/border).
    """
    H, W = depth.shape
    src = Image.fromarray(rgb)
    src_resized = src.resize((grid, grid), Image.LANCZOS)
    depth_resized = np.array(
        Image.fromarray((depth * 255).astype(np.uint8)).resize((grid, grid), Image.LANCZOS)
    ).astype(np.float32) / 255.

    xs = np.linspace(-badge_radius, badge_radius, grid)
    ys = np.linspace(-badge_radius, badge_radius, grid)
    xg, yg = np.meshgrid(xs, ys)

    # Inward displacement: bright (frame/gold) = Z=0, dark (inner scene) = Z<0
    zg = -(1.0 - depth_resized) * depth_scale

    # Pixels outside badge circle -> flat (Z=0), no displacement
    dist = np.sqrt(xg**2 + yg**2)
    outside = dist > badge_radius * 0.98
    zg[outside] = 0.

    # Smooth the transition at the badge edge
    edge_blend = np.clip((badge_radius * 0.98 - dist) / (badge_radius * 0.05), 0., 1.)
    zg *= edge_blend

    verts = np.column_stack([xg.ravel(), yg.ravel(), zg.ravel()])

    # Faces: two triangles per quad
    r, c = grid - 1, grid - 1
    ii = np.repeat(np.arange(r), c)
    jj = np.tile(np.arange(c), r)
    tl = ii * grid + jj
    tr = tl + 1
    bl = tl + grid
    br = bl + 1
    faces = np.concatenate([
        np.stack([tl, tr, bl], axis=1),
        np.stack([tr, br, bl], axis=1),
    ])

    # UV: trimesh flips V on GLTF export — set u,v without pre-flip
    u = np.tile(np.arange(grid) / (grid - 1.), grid)
    v = np.repeat(np.arange(grid) / (grid - 1.), grid)
    uvs = np.column_stack([u, v])

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    material = PBRMaterial(
        baseColorTexture=src_resized,
        metallicFactor=0.08,
        roughnessFactor=0.42,
        doubleSided=False,
    )
    mesh.visual = TextureVisuals(uv=uvs, material=material)
    return mesh


def make_glass_cover(
    badge_radius: float,
    cover_z: float,
    segments: int = 128,
) -> trimesh.Trimesh:
    """
    Transparent circular cover disc sitting cover_z units in front of the badge.

    The air gap between this cover and the recessed badge content makes the
    spatial depth immediately visible when the badge is viewed at any angle.
    Material: near-transparent with very low roughness (smooth glass/acrylic).
    """
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    verts = [[0., 0., cover_z]]
    uvs   = [[0.5, 0.5]]
    for a in angles:
        x, y = np.cos(a) * badge_radius, np.sin(a) * badge_radius
        verts.append([x, y, cover_z])
        uvs.append([x / badge_radius * 0.5 + 0.5,
                    y / badge_radius * 0.5 + 0.5])

    verts = np.array(verts, dtype=np.float64)
    uvs   = np.array(uvs,   dtype=np.float64)
    faces = []
    for i in range(segments):
        j = i % segments + 1
        k = (i + 1) % segments + 1
        faces.append([0, j, k])

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)

    # Very slight cool tint, mostly transparent, mirror-smooth glass
    material = PBRMaterial(
        baseColorFactor=[0.88, 0.93, 1.0, 0.12],   # near-invisible, faint blue tint
        metallicFactor=0.0,
        roughnessFactor=0.04,                        # very smooth
        alphaMode='BLEND',
        doubleSided=True,
    )
    mesh.visual = TextureVisuals(uv=uvs, material=material)
    return mesh


def make_side_wall(badge_radius: float, thickness: float, segments: int = 128,
                   rim_color: tuple = (180, 140, 60),
                   top_z: float = 0.) -> trimesh.Trimesh:
    """Cylinder wall spanning from top_z (cover face) down to -thickness."""
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    verts = []
    for a in angles:
        x, y = np.cos(a) * badge_radius, np.sin(a) * badge_radius
        verts += [[x, y, top_z], [x, y, -thickness]]
    verts = np.array(verts, dtype=np.float64)
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        v0, v1 = i*2, i*2+1
        v2, v3 = j*2, j*2+1
        faces += [[v0, v2, v1], [v1, v2, v3]]
    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces))
    n = len(verts)
    mesh.visual.vertex_colors = np.tile(list(rim_color) + [255], (n, 1)).astype(np.uint8)
    return mesh


def make_back(badge_radius: float, thickness: float, segments: int = 128,
              rim_color: tuple = (180, 140, 60)) -> trimesh.Trimesh:
    """Flat back face."""
    z = -thickness
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    verts = [[0., 0., z]]
    for a in angles:
        verts.append([np.cos(a) * badge_radius, np.sin(a) * badge_radius, z])
    verts = np.array(verts, dtype=np.float64)
    faces = []
    for i in range(segments):
        j = i % segments + 1
        k = (i + 1) % segments + 1
        faces.append([0, k, j])
    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces))
    n = len(verts)
    back_color = [max(0, c - 40) for c in rim_color] + [255]
    mesh.visual.vertex_colors = np.tile(back_color, (n, 1)).astype(np.uint8)
    return mesh


def main() -> None:
    ap = argparse.ArgumentParser(
        description='Spatial-depth badge GLB — single displaced surface, inward depth'
    )
    ap.add_argument('--input',       required=True,            help='Source badge PNG')
    ap.add_argument('--output',      required=True,            help='Output .glb path')
    ap.add_argument('--depth-map',   default=None,             help='Pre-computed depth map PNG (greyscale)')
    ap.add_argument('--depth-scale', type=float, default=6.,   help='How deep the inner scene recedes in 3D units (default 6)')
    ap.add_argument('--grid',        type=int,   default=384,  help='Mesh resolution NxN (default 384)')
    ap.add_argument('--badge-radius',type=float, default=50.,  help='Badge radius in 3D units (default 50)')
    ap.add_argument('--thickness',   type=float, default=4.,   help='Side wall thickness behind badge face (default 4)')
    ap.add_argument('--cover',       type=float, default=3.,   help='Glass cover height in front of badge face in 3D units (default 3)')
    ap.add_argument('--no-cover',    action='store_true',      help='Omit the transparent glass cover')
    ap.add_argument('--rim-color',   type=str,   default='196,146,89', help='Rim RGB (default 196,146,89 — gold)')
    args = ap.parse_args()

    rim = tuple(int(x) for x in args.rim_color.split(','))
    cover_z = float(args.cover)   # glass sits cover_z units in front of badge face

    print(f'Loading  : {args.input}')
    src = Image.open(args.input).convert('RGB')
    W0, H0 = src.size
    print(f'  size   : {W0}x{H0}')

    rgb = np.array(src)

    if args.depth_map:
        print(f'Depth    : loading {args.depth_map}')
        depth = np.array(Image.open(args.depth_map).convert('L')).astype(np.float32) / 255.
    else:
        print('Depth    : estimating from colour heuristics...')
        depth = get_depth(rgb)

    print(f'Mesh     : building {args.grid}x{args.grid} displaced surface (inward depth={args.depth_scale})...')
    face_mesh = build_mesh(rgb, depth,
                           badge_radius=args.badge_radius,
                           depth_scale=args.depth_scale,
                           grid=args.grid)
    print(f'  -> {len(face_mesh.vertices):,} vertices  {len(face_mesh.faces):,} faces')

    # Side wall spans from cover face down to back plate
    total_thickness = args.thickness + cover_z
    side = make_side_wall(args.badge_radius, total_thickness, rim_color=rim, top_z=cover_z)
    back = make_back(args.badge_radius, total_thickness, rim_color=rim)

    meshes = [face_mesh, side, back]

    if not args.no_cover:
        print(f'Cover    : transparent glass disc at Z=+{cover_z:.1f}...')
        cover = make_glass_cover(args.badge_radius, cover_z=cover_z)
        meshes.append(cover)

    print('Exporting: writing GLB...')
    scene = trimesh.Scene(meshes)
    scene.export(args.output)

    kb = os.path.getsize(args.output) / 1024
    print(f'Saved    : {args.output}  ({kb:.1f} KB)')
    print()
    print('Preview  : https://gltf-viewer.donmccurdy.com  (drag & drop the GLB)')
    print('  Rotate the badge -- depth visible through the glass cover.')


if __name__ == '__main__':
    main()
