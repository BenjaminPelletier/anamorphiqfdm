"""
Script to generate an anamorphic intersection mesh from three text strings using CadQuery.
"""

import argparse
import os.path
from pathlib import Path

import cadquery as cq


def _plane_with_rotation(angle_deg: float) -> cq.Plane:
    base_plane = cq.Plane.XZ()  # Normal points along +Y, giving a front-facing orientation
    return base_plane.rotated((0, angle_deg, 0))


def _create_text_prism(text: str, font: str, plane: cq.Plane, extrusion: float) -> cq.Solid:
    if os.path.exists(font):
        kw_args = {"fontPath": font}
    else:
        kw_args = {"font": font}
    workplane = cq.Workplane(plane)
    text_solid = (
        workplane
        .text(
            txt=text,
            fontsize=1.0,
            distance=extrusion * 2,
            halign="center",
            valign="center",
            combine=True,
            clean=True,
            **kw_args,
        )
        .translate(plane.zDir * -extrusion)
        .val()
    )
    return text_solid


def build_intersection(text_a: str, text_b: str, text_c: str, font: str) -> cq.Solid:
    max_len = max(len(text_a), len(text_b), len(text_c)) or 1
    extrusion = float(max_len)

    planes = (
        _plane_with_rotation(0),
        _plane_with_rotation(45),
        _plane_with_rotation(-45),
    )

    solids = [
        _create_text_prism(txt, font=font, plane=plane, extrusion=extrusion)
        for txt, plane in zip((text_a, text_b, text_c), planes)
    ]

    result = solids[0].intersect(solids[1]).intersect(solids[2])
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate an anamorphic intersection mesh from three text strings viewed from "
            "front, 45° left, and 45° right angles."
        )
    )
    parser.add_argument("text_a", help="Front-facing text")
    parser.add_argument("text_b", help="45-degree left-facing text")
    parser.add_argument("text_c", help="45-degree right-facing text")
    parser.add_argument("--font", default="Arial", help="Font name or path for CadQuery text")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("anamorphic_text.stl"),
        help="Output STL path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    final_solid = build_intersection(args.text_a, args.text_b, args.text_c, args.font)
    cq.exporters.export(final_solid, str(args.output))
    print(f"Exported intersection mesh to {args.output}")


if __name__ == "__main__":
    main()
