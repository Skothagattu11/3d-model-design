"""
depth_render.py — Apply depth-based 3D relief lighting to a badge image.

Generates a depth map from colour/luminance/position cues, derives surface
normals, then applies directional Phong lighting + cast shadows so the image
looks like a physical embossed sculpture photographed under raking light.

Dependencies: Pillow, numpy (already required by the 3d-model-skill engine)

Usage:
    python depth_render.py --input badge.png --output badge_3d.png
    python depth_render.py --input badge.png --output badge_3d.png --strength 6 --shadow-offset 7
    python depth_render.py --input badge.png --output badge_3d.png --save-depth
"""

import argparse
import math
import numpy as np
from PIL import Image, ImageFilter


# ---------------------------------------------------------------------------
# Depth estimation
# ---------------------------------------------------------------------------

def make_depth_map(rgb: np.ndarray) -> np.ndarray:
    """
    Estimate a per-pixel depth (0=far, 1=close) from colour + radial position.

    Heuristics tuned for circular badge images:
      - Background (dark pixels far from centre) -> 0
      - Stone/grey outer ring -> low-mid
      - Inner warm amber glow -> mid-high
      - Bright gold metallic -> high
      - Green laurel elements -> mid-high
      - Very bright highlights -> closest
    """
    h, w = rgb.shape[:2]
    r, g, b = rgb[:, :, 0] / 255., rgb[:, :, 1] / 255., rgb[:, :, 2] / 255.

    lum = 0.299 * r + 0.587 * g + 0.114 * b

    cmax = np.maximum(r, np.maximum(g, b))
    cmin = np.minimum(r, np.minimum(g, b))
    sat = np.where(cmax > 0.05, (cmax - cmin) / np.where(cmax > 0.05, cmax, 1.), 0.)

    # Radial weight — badge centre is always closer than edge
    cx, cy = w / 2., h / 2.
    yi, xi = np.mgrid[0:h, 0:w]
    radial = (1. - np.sqrt(((xi - cx) / cx) ** 2 + ((yi - cy) / cy) ** 2)).clip(0., 1.)

    depth = lum * 0.45 + sat * 0.20 + radial * 0.35

    # Hard background override — very dark pixels well outside the badge
    bg = (lum < 0.07) & (radial < 0.42)
    depth[bg] = 0.

    # Warm amber / orange inner glow -> pull forward
    warm = (r > 0.50) & (g > 0.25) & (b < 0.30) & (lum > 0.25)
    depth[warm] = (depth[warm] * 1.35).clip(0., 1.)

    # Bright gold metallic -> closest surface layer
    gold = (r > 0.65) & (g > 0.50) & (b < 0.38) & (lum > 0.55)
    depth[gold] = (depth[gold] * 1.55).clip(0., 1.)

    # Pure white highlights -> very close
    white = (r > 0.88) & (g > 0.88) & (b > 0.80) & (lum > 0.85)
    depth[white] = (depth[white] * 1.6).clip(0., 1.)

    # Green (laurel leaves) -> mid-high
    green = (g > r * 1.15) & (g > b * 1.4) & (lum > 0.08) & (lum < 0.75)
    depth[green] = (depth[green] * 1.22).clip(0., 1.)

    # Normalise to [0, 1]
    lo, hi = depth.min(), depth.max()
    return ((depth - lo) / (hi - lo + 1e-8)).astype(np.float32)


def smooth_depth(depth: np.ndarray, radius: int = 7) -> np.ndarray:
    pil = Image.fromarray((depth * 255).astype(np.uint8))
    return np.array(pil.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255.


def contrast_depth(depth: np.ndarray, gamma: float = 1.0, levels: float = 1.0) -> np.ndarray:
    """Apply gamma curve and level stretch to amplify depth separation."""
    d = depth ** (1.0 / gamma) if gamma != 1.0 else depth.copy()
    # S-curve: push darks darker, lights lighter
    if levels > 1.0:
        lo = np.percentile(d, 5)
        hi = np.percentile(d, 95)
        d = ((d - lo) / (hi - lo + 1e-8)).clip(0., 1.)
        d = (d ** (1.0 / levels)) * (d > 0.5) + (1. - (1. - d) ** (1.0 / levels)) * (d <= 0.5)
    return d.clip(0., 1.).astype(np.float32)


# ---------------------------------------------------------------------------
# Normal map
# ---------------------------------------------------------------------------

def compute_normals(depth: np.ndarray, strength: float) -> tuple:
    """Central-difference gradient -> surface normals."""
    gx = np.zeros_like(depth)
    gy = np.zeros_like(depth)
    gx[:, 1:-1] = (depth[:, 2:] - depth[:, :-2]) * strength
    gy[1:-1, :] = (depth[2:, :] - depth[:-2, :]) * strength
    length = np.sqrt(gx ** 2 + gy ** 2 + 1.)
    return -gx / length, -gy / length, np.ones_like(depth) / length


# ---------------------------------------------------------------------------
# Image-gradient bump map (emboss-based)
# ---------------------------------------------------------------------------

def build_emboss_lighting(rgb: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    Derive a per-pixel lighting multiplier directly from the image's own
    gradients using PIL's EMBOSS kernel.  This captures every physical edge
    in the artwork — ring bevels, leaf veins, the spike tip — without needing
    a hand-crafted depth map.

    Returns a float array shaped (H, W) centred on 1.0:
      > 1.0  lit face  (facing the light)
      < 1.0  shadow face
    """
    gray = Image.fromarray(rgb).convert('L')
    # Smooth slightly before emboss so noise doesn't create speckle
    gray = gray.filter(ImageFilter.GaussianBlur(1))
    embossed = np.array(gray.filter(ImageFilter.EMBOSS)).astype(np.float32)
    # EMBOSS output is 0–255 centred ~128; map to [-1, +1]
    bump = (embossed - 128.) / 128.
    # Scale by strength and shift so neutral = 1.0
    return 1.0 + bump * strength


# ---------------------------------------------------------------------------
# Lighting
# ---------------------------------------------------------------------------

def apply_lighting(
    rgb: np.ndarray,
    nx: np.ndarray, ny: np.ndarray, nz: np.ndarray,
    depth: np.ndarray,
    light_az: float = 210.,
    light_el: float = 45.,
    emboss_strength: float = 0.,
) -> np.ndarray:
    """Phong directional lighting: ambient + diffuse + specular + depth AO,
    optionally blended with image-gradient emboss lighting."""
    az = math.radians(light_az)
    el = math.radians(light_el)
    lx = math.cos(el) * math.cos(az)
    ly = math.cos(el) * math.sin(az)
    lz = math.sin(el)
    ln = math.sqrt(lx ** 2 + ly ** 2 + lz ** 2)
    lx, ly, lz = lx / ln, ly / ln, lz / ln

    diffuse = (nx * lx + ny * ly + nz * lz).clip(0., 1.)

    # Specular: reflection of light towards camera [0,0,1]
    dot = nx * lx + ny * ly + nz * lz
    rz = (2. * dot * nz - lz).clip(0., 1.)
    specular = rz ** 22 * 0.40

    # Subtle ambient occlusion: closer pixels are slightly brighter
    ao = 0.80 + 0.20 * depth

    luminance = (0.32 + diffuse * 0.58) * ao

    # Mix in emboss-derived lighting when requested
    if emboss_strength > 0.:
        emb = build_emboss_lighting(rgb, strength=emboss_strength)
        luminance = luminance * (1. - min(emboss_strength, 0.9)) + emb * min(emboss_strength, 0.9)

    out = rgb.astype(np.float64).copy()
    for c in range(3):
        out[:, :, c] = out[:, :, c] * luminance + specular * 230.
    return out.clip(0., 255.).astype(np.uint8)


def add_cast_shadows(
    rgb: np.ndarray,
    depth: np.ndarray,
    offset: int = 5,
    strength: float = 0.55,
    darkness: float = 0.68,
) -> np.ndarray:
    """Darken pixels that lie in the shadow cast by elevated neighbours."""
    shadow = np.zeros_like(depth)
    if offset > 0:
        shadow[offset:, offset:] = depth[:-offset, :-offset]
    mask = (shadow - depth - 0.05).clip(0., 1.) * strength
    out = rgb.astype(np.float64).copy()
    for c in range(3):
        out[:, :, c] *= (1. - mask * darkness)
    return out.clip(0., 255.).astype(np.uint8)


def add_depth_colour_grade(
    rgb: np.ndarray,
    depth: np.ndarray,
    warmth: float = 0.06,
) -> np.ndarray:
    """Closer pixels get a very subtle warm colour push (foreground pop)."""
    out = rgb.astype(np.float64).copy()
    w = depth * warmth
    out[:, :, 0] = (out[:, :, 0] * (1. + w)).clip(0., 255.)   # warm reds up
    out[:, :, 2] = (out[:, :, 2] * (1. - w * 0.4)).clip(0., 255.)  # blues back
    return out.clip(0., 255.).astype(np.uint8)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description='Generate a depth-relief 3D-effect PNG from a badge image'
    )
    ap.add_argument('--input',         required=True,            help='Source image (PNG/JPG)')
    ap.add_argument('--output',        required=True,            help='Output PNG path')
    ap.add_argument('--strength',      type=float, default=5.0,  help='Normal-map depth strength (default 5.0)')
    ap.add_argument('--shadow-offset', type=int,   default=5,    help='Cast-shadow pixel offset (default 5)')
    ap.add_argument('--light-az',      type=float, default=210., help='Light azimuth in degrees (default 210)')
    ap.add_argument('--light-el',      type=float, default=45.,  help='Light elevation in degrees (default 45)')
    ap.add_argument('--smooth-radius',   type=int,   default=7,    help='Depth map blur radius (default 7)')
    ap.add_argument('--depth-gamma',     type=float, default=1.0,  help='Depth gamma — >1 brightens (pulls forward), <1 flattens (default 1.0)')
    ap.add_argument('--depth-contrast',  type=float, default=1.0,  help='S-curve contrast on depth map (default 1.0, try 1.5–2.5 for drama)')
    ap.add_argument('--shadow-strength', type=float, default=0.55, help='Cast-shadow mask strength (default 0.55, try 0.85–1.0 for drama)')
    ap.add_argument('--shadow-darkness', type=float, default=0.68, help='How black shadows go (default 0.68, try 0.90–1.0 for drama)')
    ap.add_argument('--blend',           type=float, default=0.45, help='0=full depth effect, 1=original image. Default 0.45 blends both.')
    ap.add_argument('--emboss',          type=float, default=0.0,  help='Image-gradient emboss strength (0=off, 0.6-0.85 recommended for crisp edges)')
    ap.add_argument('--save-depth',      action='store_true',      help='Also save the depth map PNG')
    args = ap.parse_args()

    print(f'Loading  : {args.input}')
    src = Image.open(args.input)
    alpha = np.array(src.convert('RGBA'))[:, :, 3] if src.mode in ('RGBA', 'LA', 'P') else None
    rgb = np.array(src.convert('RGB'))

    print('Depth map: building...')
    depth_raw = make_depth_map(rgb)
    depth_raw = contrast_depth(depth_raw, gamma=args.depth_gamma, levels=args.depth_contrast)
    depth = smooth_depth(depth_raw, radius=args.smooth_radius)

    if args.save_depth:
        dpath = args.output.replace('.png', '_depth.png')
        Image.fromarray((depth * 255).astype(np.uint8)).save(dpath)
        print(f'  -> depth map saved: {dpath}')

    print('Normals  : computing...')
    nx, ny, nz = compute_normals(depth, args.strength)

    print('Lighting : applying Phong...')
    result = apply_lighting(rgb, nx, ny, nz, depth, args.light_az, args.light_el,
                            emboss_strength=args.emboss)

    print('Shadows  : casting...')
    result = add_cast_shadows(result, depth, offset=args.shadow_offset,
                              strength=args.shadow_strength, darkness=args.shadow_darkness)

    print('Grade    : depth colour grade...')
    result = add_depth_colour_grade(result, depth)

    # Blend with original to recover vibrancy lost to lighting
    blend = args.blend
    result = (result.astype(np.float64) * (1. - blend) + rgb.astype(np.float64) * blend)
    result = result.clip(0., 255.).astype(np.uint8)

    # Restore original alpha channel
    if alpha is not None:
        out_pil = Image.fromarray(result).convert('RGBA')
        arr = np.array(out_pil)
        arr[:, :, 3] = alpha
        out_pil = Image.fromarray(arr)
    else:
        out_pil = Image.fromarray(result)

    out_pil.save(args.output, optimize=True)
    sz = out_pil.size
    print(f'Saved    : {args.output}  ({sz[0]}×{sz[1]} px)')


if __name__ == '__main__':
    main()
