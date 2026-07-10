import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.visual import TextureVisuals

PRESETS = {
    "BrushedGold":   {"base_color": [0.83, 0.66, 0.24, 1.0], "metallic": 1.0, "roughness": 0.42},
    "PolishedSteel": {"base_color": [0.91, 0.92, 0.95, 1.0], "metallic": 1.0, "roughness": 0.10},
    "Diamond":       {"base_color": [1.00, 1.00, 1.00, 0.92], "metallic": 0.10, "roughness": 0.02, "alpha_mode": "BLEND"},
    "Chrome":        {"base_color": [0.95, 0.95, 0.95, 1.0], "metallic": 1.0, "roughness": 0.05},
    "MatteSilver":   {"base_color": [0.80, 0.80, 0.82, 1.0], "metallic": 0.9, "roughness": 0.45},
    "BlackMatte":    {"base_color": [0.05, 0.05, 0.05, 1.0], "metallic": 0.0, "roughness": 0.90},
    "RoseGold":      {"base_color": [0.91, 0.67, 0.56, 1.0], "metallic": 1.0, "roughness": 0.38},
    "Platinum":      {"base_color": [0.86, 0.87, 0.89, 1.0], "metallic": 1.0, "roughness": 0.15},
}


def apply(mesh: trimesh.Trimesh, material_spec: dict) -> trimesh.Trimesh:
    mat = PBRMaterial(
        name=material_spec["name"],
        baseColorFactor=material_spec["base_color"],
        metallicFactor=material_spec["metallic"],
        roughnessFactor=material_spec["roughness"],
    )
    if material_spec.get("alpha_mode"):
        mat.alphaMode = material_spec["alpha_mode"]
    mesh.visual = TextureVisuals(material=mat)
    return mesh
