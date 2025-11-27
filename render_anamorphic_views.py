"""Render orthographic projections of an anamorphic STL from three viewpoints.

The script loads an STL using ``trimesh`` and produces three PNG renders matching
 the front, 45° left, and 45° right camera planes used to create the original
 mesh. Views are orthographic so the resulting silhouettes reveal the input
 text.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import trimesh

from view_rendering import VIEW_ANGLES, render_views


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render orthographic projections of an anamorphic text STL from front, "
            "45° left, and 45° right viewpoints."
        )
    )
    parser.add_argument("stl", type=Path, help="Path to the anamorphic STL")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("renders"),
        help="Directory where PNG renders will be written",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=800,
        help="Square image size in pixels for each render",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    mesh = trimesh.load(args.stl, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError("Loaded geometry is not a mesh")

    render_views(mesh, size=args.size, output_dir=args.output_dir)
    for name in VIEW_ANGLES:
        print(f"Saved {name} view to {args.output_dir / f'{name}.png'}")


if __name__ == "__main__":
    main()
