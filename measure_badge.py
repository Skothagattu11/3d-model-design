"""
measure_badge.py — Auto-measure a badge image for png_to_glb.py UV settings.

Outputs:
  uv_scale       — disc radius shows exactly the badge edge
  uv_offset_x/y  — centres the badge on the disc (trimesh-flip-aware)
  rim_color      — R,G,B of the outer gold/metal trim (for --rim-color)

Usage:
    python measure_badge.py badge.png
"""
import sys
import numpy as np
from PIL import Image


def measure(path: str) -> dict:
    arr = np.array(Image.open(path).convert('RGB'))
    H, W = arr.shape[:2]
    lum = (0.299*arr[:,:,0] + 0.587*arr[:,:,1] + 0.114*arr[:,:,2]) / 255.

    # Badge bounding box (non-black pixels)
    badge_mask = lum > 0.06
    rows = np.any(badge_mask, axis=1)
    cols = np.any(badge_mask, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    bcx = (cmin + cmax) / 2.
    bcy = (rmin + rmax) / 2.
    badge_r = (cmax - cmin) / 2.   # use horizontal radius (most reliable)

    # UV parameters (trimesh flips V on GLTF export)
    # disc_centre maps to image pixel (bcx, bcy) when:
    #   u_centre = bcx/W  =>  0.5 + off_x = bcx/W  =>  off_x = bcx/W - 0.5
    #   v_gltf   = bcy/H  =>  0.5 - off_y = bcy/H  =>  off_y = 0.5 - bcy/H
    uv_offset_x = bcx / W - 0.5
    uv_offset_y = 0.5 - bcy / H

    # uv_scale so disc edge = badge edge (+2 % margin)
    uv_scale = (badge_r / (W / 2.)) * 0.5 * 1.02
    uv_scale = round(min(uv_scale, 0.499), 4)

    # Sample outer gold trim colour at 96–99 % badge radius
    yi, xi = np.mgrid[0:H, 0:W]
    frac = np.sqrt(((xi - bcx) / badge_r)**2 + ((yi - bcy) / badge_r)**2)
    trim_mask = (frac > 0.96) & (frac < 0.995) & (lum > 0.12)
    if trim_mask.any():
        rim = (
            int(arr[:,:,0][trim_mask].mean()),
            int(arr[:,:,1][trim_mask].mean()),
            int(arr[:,:,2][trim_mask].mean()),
        )
    else:
        rim = (100, 80, 55)   # fallback bronze

    return {
        'image_size':    (W, H),
        'badge_bbox':    (cmin, rmin, cmax, rmax),
        'badge_centre':  (round(bcx, 1), round(bcy, 1)),
        'badge_radius':  round(badge_r, 1),
        'uv_scale':      uv_scale,
        'uv_offset_x':   round(uv_offset_x, 4),
        'uv_offset_y':   round(uv_offset_y, 4),
        'rim_color':     rim,
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python measure_badge.py <image.png>')
        sys.exit(1)

    m = measure(sys.argv[1])
    print(f"Image       : {m['image_size'][0]}x{m['image_size'][1]}")
    print(f"Badge bbox  : x=[{m['badge_bbox'][0]},{m['badge_bbox'][2]}]  y=[{m['badge_bbox'][1]},{m['badge_bbox'][3]}]")
    print(f"Badge centre: {m['badge_centre']}  (image centre: ({m['image_size'][0]/2},{m['image_size'][1]/2}))")
    print(f"Badge radius: {m['badge_radius']} px")
    print()
    print(f"uv_scale    : {m['uv_scale']}")
    print(f"uv_offset_x : {m['uv_offset_x']}")
    print(f"uv_offset_y : {m['uv_offset_y']}")
    print(f"rim_color   : {m['rim_color'][0]},{m['rim_color'][1]},{m['rim_color'][2]}")
    print()
    print("-- depth_render.py command --")
    print(f"python depth_render.py --input <badge.png> --output <badge_depth.png> \\")
    print(f"  --strength 8.0 --shadow-offset 10 --shadow-strength 0.78 --shadow-darkness 0.88 \\")
    print(f"  --depth-contrast 1.7 --smooth-radius 5 --light-el 38 --light-az 215 \\")
    print(f"  --emboss 0.68 --blend 0.42")
    print()
    print("-- png_to_glb.py command --")
    print(f"python png_to_glb.py --input <badge_depth.png> --output <badge_medal.glb> \\")
    print(f"  --thickness 6 --uv-scale {m['uv_scale']} \\")
    print(f"  --uv-offset-x {m['uv_offset_x']} --uv-offset-y {m['uv_offset_y']} \\")
    print(f"  --rim-color \"{m['rim_color'][0]},{m['rim_color'][1]},{m['rim_color'][2]}\"")
