"""Render orthographic projections of an anamorphic STL from three viewpoints.

The script loads an STL using ``trimesh`` and produces three PNG renders matching
 the front, 45° left, and 45° right camera planes used to create the original
 mesh. Views are orthographic so the resulting silhouettes reveal the input
 text.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np
import trimesh


def _rotation_about_z(angle_deg: float) -> np.ndarray:
    """Return a rotation matrix for rotation about the Z axis."""

    angle_rad = np.deg2rad(angle_deg)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    return np.array(
        [
            [cos_a, -sin_a, 0.0],
            [sin_a, cos_a, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )


def _build_view_direction(base: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate ``base`` around Z by ``angle_deg`` degrees."""

    rotated = _rotation_about_z(angle_deg) @ base
    return rotated / np.linalg.norm(rotated)


def _projection_basis(view_dir: np.ndarray) -> np.ndarray:
    """Create an orthonormal basis for projecting onto a plane.

    The resulting matrix has columns ``(right, up, forward)``.
    """

    view_dir = view_dir / np.linalg.norm(view_dir)
    up = np.array([0.0, 0.0, -1.0])
    if np.allclose(np.cross(view_dir, up), 0.0):
        up = np.array([1.0, 0.0, 0.0])

    right = np.cross(view_dir, up)
    right /= np.linalg.norm(right)
    true_up = np.cross(view_dir, right)
    true_up /= np.linalg.norm(true_up)

    return np.stack([right, true_up, view_dir], axis=1)


def _project_vertices(mesh: trimesh.Trimesh, view_dir: np.ndarray) -> np.ndarray:
    """Project mesh vertices into 2D coordinates for an orthographic view."""

    basis = _projection_basis(view_dir)
    # Drop the forward component to keep only in-plane coordinates
    return mesh.vertices @ basis[:, :2]


def _render_projection(
    mesh: trimesh.Trimesh,
    view_dir: np.ndarray,
    output_path: Path,
    size: int,
) -> None:
    """Render a single orthographic projection to ``output_path``."""

    projected = _project_vertices(mesh, view_dir)
    faces_2d = projected[mesh.faces]

    fig, ax = plt.subplots(figsize=(size / 100, size / 100), dpi=100)

    polygons = [face for face in faces_2d]
    collection = PolyCollection(
        polygons,
        closed=True,
        facecolor="black",
        edgecolor="black",
        linewidth=0.2,
    )
    ax.add_collection(collection)

    min_x, min_y = projected.min(axis=0)
    max_x, max_y = projected.max(axis=0)
    span_x = max_x - min_x
    span_y = max_y - min_y
    margin_x = span_x * 0.05 or 1.0
    margin_y = span_y * 0.05 or 1.0

    ax.set_xlim(min_x - margin_x, max_x + margin_x)
    ax.set_ylim(min_y - margin_y, max_y + margin_y)
    ax.set_aspect("equal")
    ax.axis("off")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


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

    base_dir = np.array([0.0, -1.0, 0.0])
    view_angles: Dict[str, float] = {
        "front": 0.0,
        "left": 45.0,
        "right": -45.0,
    }

    for name, angle in view_angles.items():
        direction = _build_view_direction(base_dir, angle)
        output_path = args.output_dir / f"{name}.png"
        _render_projection(mesh, direction, output_path, args.size)
        print(f"Saved {name} view to {output_path}")


if __name__ == "__main__":
    main()
