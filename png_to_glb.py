"""
png_to_glb.py — Wrap a PNG badge onto a circular GLB medal disc.

No background removal — the image is used as-is.
The circular disc naturally hides the square image corners.
Side walls + back plate give physical badge thickness.

Usage:
    python png_to_glb.py --input badge.png --output badge.glb
    python png_to_glb.py --input badge.png --output badge.glb --thickness 6
"""

import argparse
import os
import numpy as np
from PIL import Image
import trimesh
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial


def make_disc_face(img: Image.Image,
                   radius: float = 50.,
                   segments: int = 128,
                   uv_scale: float = 0.45,
                   uv_offset_x: float = 0.0,
                   uv_offset_y: float = 0.0) -> trimesh.Trimesh:
    """
    Circular disc with the badge image mapped onto it.

    uv_scale < 0.5 zooms into the central badge area, so the badge fills
    the disc instead of showing the full image (including dark borders).
    0.45 maps the central 90 % of the image width onto the disc diameter.

    uv_offset_x / uv_offset_y nudge the image centre on the disc (+ = right/up).

    trimesh flips V internally when writing GLTF, so we do NOT pre-flip V.
    """
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)

    verts = [[0., 0., 0.]]       # centre
    uvs   = [[0.5 + uv_offset_x, 0.5 + uv_offset_y]]

    for a in angles:
        x, y = np.cos(a) * radius, np.sin(a) * radius
        verts.append([x, y, 0.])
        uvs.append([x / radius * uv_scale + 0.5 + uv_offset_x,
                    y / radius * uv_scale + 0.5 + uv_offset_y])

    verts = np.array(verts, dtype=np.float64)
    uvs   = np.array(uvs,   dtype=np.float64)

    faces = []
    for i in range(segments):
        j = i % segments + 1
        k = (i + 1) % segments + 1
        faces.append([0, j, k])

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    material = PBRMaterial(
        baseColorTexture=img.convert('RGB'),
        metallicFactor=0.05,
        roughnessFactor=0.45,
    )
    mesh.visual = TextureVisuals(uv=uvs, material=material)
    return mesh


def make_side_walls(radius: float = 50.,
                    thickness: float = 5.,
                    segments: int = 128,
                    rim_color: tuple = (50, 38, 20)) -> trimesh.Trimesh:
    """Cylindrical side wall coloured to match the badge rim."""
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    verts = []
    for a in angles:
        x, y = np.cos(a) * radius, np.sin(a) * radius
        verts += [[x, y, 0.], [x, y, -thickness]]

    verts = np.array(verts, dtype=np.float64)
    faces = []
    for i in range(segments):
        j  = (i + 1) % segments
        v0, v1 = i * 2,     i * 2 + 1
        v2, v3 = j * 2,     j * 2 + 1
        faces += [[v0, v2, v1], [v1, v2, v3]]

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces))
    n = len(verts)
    color = list(rim_color) + [255]
    mesh.visual.vertex_colors = np.tile(color, (n, 1)).astype(np.uint8)
    return mesh


def make_back_disc(radius: float = 50.,
                   thickness: float = 5.,
                   segments: int = 128,
                   rim_color: tuple = (18, 14, 10)) -> trimesh.Trimesh:
    """Flat dark back face (reversed winding so normal faces away)."""
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    z = -thickness
    verts = [[0., 0., z]]
    for a in angles:
        verts.append([np.cos(a) * radius, np.sin(a) * radius, z])

    verts = np.array(verts, dtype=np.float64)
    faces = []
    for i in range(segments):
        j = i % segments + 1
        k = (i + 1) % segments + 1
        faces.append([0, k, j])   # reversed winding for back face

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces))
    n = len(verts)
    back_color = [max(0, c - 30) for c in rim_color] + [255]
    mesh.visual.vertex_colors = np.tile(back_color, (n, 1)).astype(np.uint8)
    return mesh


def main() -> None:
    ap = argparse.ArgumentParser(
        description='Wrap a PNG badge onto a circular GLB medal'
    )
    ap.add_argument('--input',     required=True,            help='Badge PNG')
    ap.add_argument('--output',    required=True,            help='Output .glb path')
    ap.add_argument('--radius',    type=float, default=50.,  help='Disc radius in 3D units (default 50)')
    ap.add_argument('--thickness', type=float, default=5.,   help='Badge thickness (default 5)')
    ap.add_argument('--segments',   type=int,   default=128,   help='Disc edge smoothness (default 128)')
    ap.add_argument('--uv-scale',   type=float, default=0.45,  help='UV zoom: 0.5=full image, 0.45=central 90%% (default 0.45)')
    ap.add_argument('--uv-offset-x',type=float, default=0.0,   help='Horizontal UV nudge, + shifts image right (default 0)')
    ap.add_argument('--uv-offset-y',type=float, default=0.0,   help='Vertical UV nudge, + shifts image up (default 0)')
    ap.add_argument('--no-back',    action='store_true',       help='Omit back face')
    ap.add_argument('--rim-color',  type=str, default='50,38,20',
                    help='Side wall RGB colour as R,G,B (0-255). Default: 50,38,20')
    args = ap.parse_args()

    rim_color = tuple(int(x) for x in args.rim_color.split(','))

    print(f'Loading   : {args.input}')
    img = Image.open(args.input)
    W, H = img.size
    print(f'  size    : {W}x{H}')
    print(f'  rim     : RGB{rim_color}')

    meshes = []

    print('Disc face : building front...')
    meshes.append(make_disc_face(img, radius=args.radius, segments=args.segments,
                                 uv_scale=args.uv_scale,
                                 uv_offset_x=args.uv_offset_x,
                                 uv_offset_y=args.uv_offset_y))

    print('Side walls: building rim...')
    meshes.append(make_side_walls(radius=args.radius, thickness=args.thickness,
                                  segments=args.segments, rim_color=rim_color))

    if not args.no_back:
        print('Back face : building back...')
        meshes.append(make_back_disc(radius=args.radius, thickness=args.thickness,
                                     segments=args.segments, rim_color=rim_color))

    print('Exporting : writing GLB...')
    scene = trimesh.Scene(meshes)
    scene.export(args.output)

    kb = os.path.getsize(args.output) / 1024
    print(f'Saved     : {args.output}  ({kb:.1f} KB)')
    print()
    print('Preview   : https://gltf-viewer.donmccurdy.com  (drag & drop the GLB)')


if __name__ == '__main__':
    main()
