# 3D Model Skill — Project Context

This repo contains two 3D badge/medal workflows. When the user asks to make a badge 3D or convert a badge to GLB, use the badge-to-3D pipeline below.

---

## Badge-to-3D Pipeline (primary workflow)

Three scripts convert any circular PNG badge into a GLB medal:

```
measure_badge.py   →   depth_render.py   →   png_to_glb.py
    (measure)            (depth PNG)           (disc GLB)
```

### Step 1 — Measure the badge

```bash
python measure_badge.py output/<badge>.png
```

Prints: `uv_scale`, `uv_offset_x`, `uv_offset_y`, `rim_color` — use these in Step 3.

### Step 2 — Apply depth rendering

```bash
python depth_render.py \
  --input  output/<badge>.png \
  --output output/<badge>_depth.png \
  --strength 8.0 --shadow-offset 10 --shadow-strength 0.78 --shadow-darkness 0.88 \
  --depth-contrast 1.7 --smooth-radius 5 \
  --light-el 38 --light-az 215 --emboss 0.68 --blend 0.42
```

### Step 3 — Build the GLB medal

```bash
python png_to_glb.py \
  --input  output/<badge>_depth.png \
  --output output/<badge>_medal.glb \
  --thickness 6 \
  --uv-scale <from step 1> \
  --uv-offset-x <from step 1> --uv-offset-y <from step 1> \
  --rim-color "<R,G,B from step 1>"
```

Preview at: https://gltf-viewer.donmccurdy.com

### UV alignment rules (if badge is off-centre on the disc)

- Badge too HIGH on disc → increase `--uv-offset-y` by 0.02
- Badge too LOW on disc  → decrease `--uv-offset-y` by 0.02
- Badge too LEFT         → decrease `--uv-offset-x` by 0.02
- Badge too RIGHT        → increase `--uv-offset-x` by 0.02

trimesh flips V when exporting GLTF. The formula from measure_badge.py is already correct.

---

## Geometric 3D Model Pipeline (for building models from scratch)

Uses `generate_3d.py` + `engine/` to build models from a GeometrySpec JSON.

```bash
python generate_3d.py --spec fixtures/<name>_spec.json --output output/
```

The `/3d-model` Claude Code skill (SKILL.md) describes the full GeometrySpec format.

---

## Project Layout

```
depth_render.py       — depth relief lighting for PNG badges
png_to_glb.py         — wrap PNG onto circular disc GLB with rim + back plate
measure_badge.py      — auto-measure badge centre, radius, rim colour
generate_3d.py        — CLI for geometric model builder
engine/               — geometric model builder (revolve, extrude, gem)
fixtures/             — GeometrySpec JSON sample files
tests/                — test suite (pytest)
SKILL.md              — /3d-model Claude Code skill definition
output/               — generated files (gitignored)
requirements.txt      — Python dependencies
```

## Dependencies

```bash
pip install -r requirements.txt
```

Requires: Pillow, numpy, trimesh, shapely
