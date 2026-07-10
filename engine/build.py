import os
import trimesh
from .schema import validate
from .primitives import revolve, extrude, convex_hull_gem
from .materials import apply


def build(spec: dict, output_dir: str, name: str | None = None) -> str:
    validate(spec)
    os.makedirs(output_dir, exist_ok=True)

    scene = trimesh.Scene()

    for comp in spec["components"]:
        t = comp["type"]
        try:
            if t == "revolve":
                mesh = revolve(comp["profile"], comp.get("sections", 256))
            elif t == "extrude":
                mesh = extrude(comp["profile"], comp["height"])
            elif t == "convex_hull_gem":
                mesh = convex_hull_gem(comp["points"])
            else:
                print(f"WARNING: unknown component type '{t}' for '{comp['name']}' — skipping")
                continue
        except Exception as exc:
            print(f"WARNING: failed to build component '{comp['name']}' ({t}): {exc}")
            continue

        apply(mesh, comp["material"])
        scene.add_geometry(mesh, node_name=comp["name"])

        print(
            f"{comp['name']:20s}  verts={len(mesh.vertices):6d}  "
            f"faces={len(mesh.faces):6d}  watertight={mesh.is_watertight}"
        )

    glb_name = (name or spec["object_name"]) + ".glb"
    out_path = os.path.join(output_dir, glb_name)
    scene.export(out_path)
    print(f"GLB written: {out_path} ({round(os.path.getsize(out_path) / 1024, 1)} KB)")

    return os.path.abspath(out_path)
