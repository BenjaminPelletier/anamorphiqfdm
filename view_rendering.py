"""Shared utilities for rendering anamorphic STL views.

The helpers in this module provide orthographic renders matching the three
viewpoints used to assess anamorphic text meshes. Both ``render_anamorphic_views``
 and ``reduce_geometry`` rely on these functions to ensure consistent output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping

import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np
import trimesh

BASE_VIEW_DIRECTION = np.array([0.0, -1.0, 0.0])
VIEW_ANGLES: Mapping[str, float] = {
    "front": 0.0,
    "left": 45.0,
    "right": -45.0,
}


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
    size: int,
    output_path: Path | None,
) -> np.ndarray:
    """Render a single orthographic projection.

    The returned image is an ``(H, W, 4)`` RGBA array with a white background and
    black geometry. If ``output_path`` is provided the PNG is also written to
    disk.
    """

    projected = _project_vertices(mesh, view_dir)
    faces_2d = projected[mesh.faces]

    fig, ax = plt.subplots(figsize=(size / 100, size / 100), dpi=100)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    polygons = [face for face in faces_2d]
    collection = PolyCollection(
        polygons,
        closed=True,
        facecolor="black",
        edgecolor="black",
        linewidth=0.2,
        antialiased=True,
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

    fig.canvas.draw()
    image = np.asarray(fig.canvas.buffer_rgba())

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, bbox_inches="tight", pad_inches=0)

    plt.close(fig)
    return image


def render_views(
    mesh: trimesh.Trimesh, *, size: int = 800, output_dir: Path | None = None
) -> Dict[str, np.ndarray]:
    """Render all standard anamorphic views.

    Args:
        mesh: The mesh to render.
        size: Square image size in pixels.
        output_dir: Directory to write PNGs. If omitted images are only returned.

    Returns:
        Mapping of view name to RGBA image arrays.
    """

    renders: Dict[str, np.ndarray] = {}
    for name, angle in VIEW_ANGLES.items():
        direction = _build_view_direction(BASE_VIEW_DIRECTION, angle)
        output_path = (output_dir / f"{name}.png") if output_dir else None
        renders[name] = _render_projection(mesh, direction, size, output_path)
    return renders
