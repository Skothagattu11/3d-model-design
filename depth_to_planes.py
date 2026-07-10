"""
depth_to_planes.py — Spatial depth GLB from a badge image.

Splits the badge into N transparent planes stacked at different Z depths.
Rotating the GLB in any viewer reveals genuine parallax — the figure floats
in front of the sun, which floats in front of the mountains, etc.

Pipeline:
    python measure_badge.py badge.png          # get badge dimensions
    python depth_to_planes.py --input badge.png --output badge_spatial.glb

Usage:
    python depth_to_planes.py --input badge.png --output badge_spatial.glb
    python depth_to_planes.py --input badge.png --output badge_spatial.glb \\
        --layers 5 --depth-spread 35 --feather 18 --badge-size 100
"""

import argparse
import os
import numpy as np
from PIL import Image, ImageFilter
import trimesh
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial

from depth_render import make_depth_map, smooth_depth, contrast_depth


# ---------------------------------------------------------------------------
# Depth map
# ---------------------------------------------------------------------------

def get_depth_map(rgb: np.ndarray) -> np.ndarray:
    """Build a depth map using colour/luminance heuristics."""
    depth = make_depth_map(rgb)
    depth = contrast_depth(depth, gamma=0.8, levels=1.8)
    depth = smooth_depth(depth, radius=4)
    return depth


def badge_circle_mask(H: int, W: int, bcx: float, bcy: float, r: float) -> np.ndarray:
    """Boolean mask for pixels inside the badge circle."""
    yi, xi = np.mgrid[0:H, 0:W]
    return ((xi - bcx) ** 2 + (yi - bcy) ** 2) <= r ** 2


# ---------------------------------------------------------------------------
# Layer extraction
# ---------------------------------------------------------------------------

def build_base_rgba(
    rgb: np.ndarray,
    circle_mask: np.ndarray,
    feather: int = 6,
) -> Image.Image:
    """
    Full badge image as the solid base layer — visible everywhere inside
    the badge circle. This is always the rearmost plane and ensures the badge
    looks complete from any viewing angle.
    """
    H, W = rgb.shape[:2]
    alpha = circle_mask.astype(np.float32) * 255.

    if feather > 0:
        pil_mask = Image.fromarray(alpha.astype(np.uint8), mode='L')
        pil_mask = pil_mask.filter(ImageFilter.GaussianBlur(feather))
        alpha = np.array(pil_mask).astype(np.float32)

    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb
    rgba[:, :, 3] = alpha.clip(0, 255).astype(np.uint8)
    return Image.fromarray(rgba, mode='RGBA')


def build_popup_rgba(
    rgb: np.ndarray,
    depth: np.ndarray,
    circle_mask: np.ndarray,
    threshold: float,
    feather: int = 10,
) -> Image.Image:
    """
    Floating pop-out layer: only pixels with depth >= threshold are visible.
    Pixels below threshold → alpha=0, so you see through to the base layer.
    Feather is applied to the depth mask edges only (not the circle edge),
    so from the side this layer shows only the foreground element shapes,
    NOT a full glowing disc.
    """
    H, W = rgb.shape[:2]

    # Depth mask: only foreground content
    depth_mask = (depth >= threshold).astype(np.float32)
    depth_mask *= circle_mask.astype(np.float32)

    if feather > 0:
        pil_mask = Image.fromarray((depth_mask * 255).astype(np.uint8), mode='L')
        pil_mask = pil_mask.filter(ImageFilter.GaussianBlur(feather))
        alpha = np.array(pil_mask).astype(np.float32)
    else:
        alpha = depth_mask * 255.

    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb
    rgba[:, :, 3] = alpha.clip(0, 255).astype(np.uint8)
    return Image.fromarray(rgba, mode='RGBA')


# ---------------------------------------------------------------------------
# Plane mesh
# ---------------------------------------------------------------------------

def make_plane_mesh(
    layer_img: Image.Image,
    size: float,
    z: float,
) -> trimesh.Trimesh:
    """
    Flat quad at given Z with the layer RGBA image as texture.

    trimesh flips V on GLTF export, so we set UV without pre-flipping.
    """
    h = size / 2.0

    verts = np.array([
        [-h, -h, z],
        [ h, -h, z],
        [ h,  h, z],
        [-h,  h, z],
    ], dtype=np.float64)

    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)

    # UV: (0,0) bottom-left, (1,1) top-right — trimesh flips V during export
    uvs = np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 1.0],
        [0.0, 1.0],
    ], dtype=np.float64)

    material = PBRMaterial(
        baseColorTexture=layer_img,
        alphaMode='BLEND',
        doubleSided=True,
        metallicFactor=0.05,
        roughnessFactor=0.55,
    )

    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    mesh.visual = TextureVisuals(uv=uvs, material=material)
    return mesh


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_spatial_glb(
    input_path: str,
    output_path: str,
    n_layers: int = 5,
    depth_spread: float = 35.0,
    feather: int = 18,
    badge_size: float = 100.0,
    depth_map_path: str = None,
    texture_size: int = 1024,
) -> None:

    print(f'Loading   : {input_path}')
    src = Image.open(input_path).convert('RGB')
    W, H = src.size
    print(f'  size    : {W}x{H}')

    # Resize for texture embedding — keeps GLB file size reasonable
    if texture_size and (W > texture_size or H > texture_size):
        src = src.resize((texture_size, texture_size), Image.LANCZOS)
        W, H = src.size
        print(f'  resized : {W}x{H} for texture embedding')

    rgb = np.array(src)

    # Depth map
    if depth_map_path:
        print(f'Depth     : loading {depth_map_path}')
        depth = np.array(Image.open(depth_map_path).convert('L')).astype(np.float32) / 255.
    else:
        print('Depth     : building from colour heuristics...')
        depth = get_depth_map(rgb)

    # Badge circle (auto-detect from non-black pixels)
    lum = (0.299*rgb[:,:,0] + 0.587*rgb[:,:,1] + 0.114*rgb[:,:,2]) / 255.
    badge_px = lum > 0.06
    rows = np.any(badge_px, axis=1)
    cols = np.any(badge_px, axis=0)
    rmin, rmax = np.where(rows)[0][[0,-1]]
    cmin, cmax = np.where(cols)[0][[0,-1]]
    bcx = (cmin + cmax) / 2.
    bcy = (rmin + rmax) / 2.
    badge_r_px = (cmax - cmin) / 2. * 1.01   # tiny margin so edge isn't cut
    print(f'  badge   : centre ({bcx:.0f},{bcy:.0f})  radius {badge_r_px:.0f}px')

    circle_mask = badge_circle_mask(H, W, bcx, bcy, badge_r_px)

    meshes = []

    # --- Base layer (complete badge, rearmost) --------------------------------
    print(f'  Base    : full badge image  Z={-depth_spread:+.1f}')
    base_rgba = build_base_rgba(rgb, circle_mask, feather=6)
    meshes.append(make_plane_mesh(base_rgba, size=badge_size, z=-depth_spread))

    # --- Pop-out layers (foreground elements only, floating above base) -------
    # n_layers pop-out planes between Z=(-depth_spread + step) and Z=0
    # Each shows only pixels above a depth threshold — tight masks, no full discs
    thresholds = np.linspace(0.35, 0.80, n_layers)     # depth cut-offs
    z_steps    = np.linspace(-depth_spread * 0.6, 0.0, n_layers)  # Z positions

    for i, (thresh, z) in enumerate(zip(thresholds, z_steps)):
        label = 'foreground' if i == n_layers - 1 else f'popup {i}'
        print(f'  Popup {i} : depth >={thresh:.2f}  Z={z:+.1f}  ({label})')
        popup_rgba = build_popup_rgba(rgb, depth, circle_mask, thresh, feather)
        meshes.append(make_plane_mesh(popup_rgba, size=badge_size, z=float(z)))

    print('Exporting : writing GLB...')
    scene = trimesh.Scene(meshes)
    scene.export(output_path)

    kb = os.path.getsize(output_path) / 1024
    print(f'Saved     : {output_path}  ({kb:.1f} KB)')
    print()
    print('Preview   : https://gltf-viewer.donmccurdy.com  (drag & drop the GLB)')
    print('            Rotate the badge — you will see parallax depth.')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description='Build a spatial-depth GLB from a badge image (multi-plane parallax)'
    )
    ap.add_argument('--input',        required=True,            help='Source badge PNG')
    ap.add_argument('--output',       required=True,            help='Output .glb path')
    ap.add_argument('--depth-map',    default=None,             help='Pre-computed depth map PNG (greyscale). If omitted, auto-generated.')
    ap.add_argument('--layers',       type=int,   default=5,    help='Number of depth planes (default 5)')
    ap.add_argument('--depth-spread', type=float, default=35.,  help='Total Z distance front-to-back in 3D units (default 35)')
    ap.add_argument('--feather',      type=int,   default=18,   help='Alpha feather radius at layer edges in pixels (default 18)')
    ap.add_argument('--badge-size',   type=float, default=100., help='Badge diameter in 3D units (default 100)')
    ap.add_argument('--texture-size', type=int,   default=1024, help='Resize textures to this size before embedding (default 1024, use 512 for smaller file)')
    args = ap.parse_args()

    build_spatial_glb(
        input_path=args.input,
        output_path=args.output,
        n_layers=args.layers,
        depth_spread=args.depth_spread,
        feather=args.feather,
        badge_size=args.badge_size,
        depth_map_path=args.depth_map,
        texture_size=args.texture_size,
    )


if __name__ == '__main__':
    main()
