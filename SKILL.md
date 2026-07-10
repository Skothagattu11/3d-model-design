---
name: 3d-model
description: Generate a 3D GLB model from an image using surface revolution, extrusion, or convex hull — upload image in Claude Code then call /3d-model
trigger: /3d-model
---

# /3d-model

Generate a production-quality `.glb` 3D model from an image already in the conversation.

## Usage

```
/3d-model                        # analyze image in conversation → propose spec → build GLB
/3d-model --output <dir>         # write GLB to specified directory (default: ./output)
/3d-model --name <name>          # override GLB filename (no extension)
```

---

## Your Sequence (follow exactly, do not skip steps)

### Step 1 — Analyze the image

Examine the image in the conversation. For each distinct part of the object identify:

**Symmetry type:**
- `revolve` — looks identical when rotated around a center axis (rings, coins, medals, discs, knobs, jars)
- `extrude` — flat 2D shape with uniform depth (logo plaques, panels, signs)
- `convex_hull_gem` — faceted cut stone (round brilliant, oval, cushion)

**Components:** list each separate material/shape region as its own component.

**Dimensions:** treat the widest extent of the full object as ~100 units. Estimate `r` (radius) and `z` (height) for profile points accordingly.

**Material from visual cues:**
- Warm yellow with linear grain → BrushedGold (metallic=1.0, roughness=0.38–0.45)
- Cool silver, mirror-like → PolishedSteel or Chrome (metallic=1.0, roughness=0.05–0.15)
- Faceted transparent stone → Diamond (metallic=0.1, roughness=0.02, alpha_mode=BLEND, alpha=0.92)
- Pink/rose metal → RoseGold (metallic=1.0, roughness=0.38)
- Dark matte → BlackMatte (metallic=0.0, roughness=0.9)
- Satin silver → MatteSilver (metallic=0.9, roughness=0.45)
- Cool white metal → Platinum (metallic=1.0, roughness=0.15)

### Step 2 — Present the GeometrySpec

Show a human-readable summary first:

```
GEOMETRY SPEC — <object_name>

Component 1: <name>  [revolve, <N> profile points]
  Radius: <r_inner>–<r_outer> units  |  Height: <z_max> units
  Material: <preset_name> (metallic=<X>, roughness=<Y>)

Component 2: <name>  [revolve, ...]
  ...
```

Then show the full raw JSON.

**Ask:** "Does this spec look right? Approve or tell me what to adjust."

### Step 3 — Wait for approval

Do NOT proceed until the user says the spec is correct. If they request changes, update the spec and show it again.

### Step 4 — Write spec and run builder

Once approved:

1. Determine output directory:
   - If user passed `--output <dir>`: use that path
   - Otherwise: use `./output` relative to current working directory

2. Write the spec JSON to `<output_dir>/<object_name>_spec.json`

3. Find the skill directory. It is located at:
   `C:\Users\skothagattu\.claude\skills\3d-model\`
   (or the symlink target if using a symlink)

4. Run:
```bash
python "C:\Users\skothagattu\.claude\skills\3d-model\generate_3d.py" \
  --spec "<output_dir>\<object_name>_spec.json" \
  --output "<output_dir>"
```

5. Report the printed stats back to the user.

### Step 5 — Offer refinement

Ask: "Want to adjust anything — groove depth, material roughness, profile points, or add/remove a component?"

---

## GeometrySpec JSON Reference

```json
{
  "object_name": "snake_case_name",
  "components": [
    {
      "name": "component_name",
      "type": "revolve",
      "profile": [[r, z], [r, z], ...],
      "sections": 256,
      "material": {
        "name": "BrushedGold",
        "base_color": [R, G, B, A],
        "metallic": 1.0,
        "roughness": 0.42,
        "alpha_mode": null
      }
    },
    {
      "name": "panel",
      "type": "extrude",
      "profile": [[x, y], [x, y], ...],
      "height": 3.0,
      "material": { ... }
    },
    {
      "name": "stone",
      "type": "convex_hull_gem",
      "points": [[x, y, z], ...],
      "material": {
        "name": "Diamond",
        "base_color": [1.0, 1.0, 1.0, 0.92],
        "metallic": 0.10,
        "roughness": 0.02,
        "alpha_mode": "BLEND"
      }
    }
  ]
}
```

**Profile tips for `revolve`:**
- Start and end at the same point to close the profile
- Chamfers: add an intermediate point offset 1–2 units at each corner
- `r` (first value) must always be >= 0
- Grooves: create a sequence like `[r, z_high], [r-0.5, z_mid], [r-1.0, z_low], [r-0.5, z_mid2], [r, z_high2]`

**Profile tips for `convex_hull_gem`:**
- Need at least 4 non-coplanar points
- Girdle ring: 8–16 points at radius=r, z=z_girdle and z=z_girdle+0.25 (offset ring for facets)
- Crown: 8 points at radius=r*0.55, z=z_girdle+r*0.42
- Culet: single point at [0, 0, z_girdle - r*0.55]

---

## Material Presets Quick Reference

| Preset name | Use for |
|---|---|
| BrushedGold | Warm yellow gold with linear grain |
| PolishedSteel | Mirror-polished silver |
| Diamond | Cut transparent gemstone (use alpha_mode=BLEND) |
| Chrome | High-gloss chrome |
| MatteSilver | Satin/matte silver finish |
| BlackMatte | Dark matte surfaces |
| RoseGold | Pink/rose gold |
| Platinum | Cool white precious metal |
