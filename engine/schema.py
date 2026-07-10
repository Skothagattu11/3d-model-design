from typing import TypedDict, Optional

VALID_TYPES = {"revolve", "extrude", "convex_hull_gem"}


class MaterialSpec(TypedDict):
    name: str
    base_color: list
    metallic: float
    roughness: float
    alpha_mode: Optional[str]


class ComponentSpec(TypedDict, total=False):
    name: str
    type: str
    profile: list
    points: list
    sections: int
    height: float
    material: MaterialSpec


class GeometrySpec(TypedDict):
    object_name: str
    components: list


def validate(spec: dict) -> None:
    if "object_name" not in spec:
        raise ValueError("Missing required field: object_name")
    if "components" not in spec:
        raise ValueError("Missing required field: components")

    for i, comp in enumerate(spec["components"]):
        p = f"components[{i}]"
        for field in ("name", "type", "material"):
            if field not in comp:
                raise ValueError(f"{p}: missing required field '{field}'")

        t = comp["type"]
        if t not in VALID_TYPES:
            raise ValueError(f"{p}: unknown type '{t}' (must be one of {sorted(VALID_TYPES)})")

        if t == "revolve":
            if "profile" not in comp:
                raise ValueError(f"{p}: revolve requires 'profile'")
            for j, pt in enumerate(comp["profile"]):
                if pt[0] < 0:
                    raise ValueError(
                        f"{p}.profile[{j}]: r must be >= 0, got {pt[0]}"
                    )

        elif t == "extrude":
            if "profile" not in comp:
                raise ValueError(f"{p}: extrude requires 'profile'")
            if "height" not in comp:
                raise ValueError(f"{p}: extrude requires 'height'")

        elif t == "convex_hull_gem":
            if "points" not in comp:
                raise ValueError(f"{p}: convex_hull_gem requires 'points'")
            if len(comp["points"]) < 4:
                raise ValueError(
                    f"{p}: convex_hull_gem requires at least 4 points, got {len(comp['points'])}"
                )

        mat = comp["material"]
        for field in ("name", "base_color", "metallic", "roughness"):
            if field not in mat:
                raise ValueError(f"{p}.material: missing required field '{field}'")
        if len(mat["base_color"]) != 4:
            raise ValueError(
                f"{p}.material.base_color: must have 4 elements [R,G,B,A], got {len(mat['base_color'])}"
            )
