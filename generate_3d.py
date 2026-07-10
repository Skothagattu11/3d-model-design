#!/usr/bin/env python3
import argparse
import json
import sys

from engine.build import build
from engine.schema import validate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a 3D GLB from a GeometrySpec JSON file"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--spec", help="Path to GeometrySpec JSON file")
    group.add_argument("--stdin", action="store_true", help="Read spec from stdin")
    parser.add_argument("--output", required=True, help="Output directory for GLB file")
    parser.add_argument("--name", help="Override GLB filename (without .glb extension)")
    parser.add_argument(
        "--validate-only", action="store_true",
        help="Validate spec without building any geometry"
    )
    args = parser.parse_args()

    if args.stdin:
        spec = json.load(sys.stdin)
    else:
        with open(args.spec) as f:
            spec = json.load(f)

    if args.validate_only:
        try:
            validate(spec)
            print("Spec is valid.")
            return 0
        except ValueError as exc:
            print(f"Spec validation failed: {exc}", file=sys.stderr)
            return 1

    try:
        build(spec, args.output, args.name)
        return 0
    except ValueError as exc:
        print(f"Spec validation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
