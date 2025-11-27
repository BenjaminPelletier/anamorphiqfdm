"""
Reduce an STL by removing components that do not affect the anamorphic renders.
"""

import argparse
from pathlib import Path
from typing import Dict, Iterable, Tuple

import numpy as np
import trimesh

from view_rendering import render_views

CLEARANCE = 0.01  # Distance above the ground plane used to remove components.
DEFAULT_IMAGE_SIZE = 800
DIFFERENCE_THRESHOLD = 0.001  # Maximum fraction of changed pixels tolerated.


def _default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_reduced{input_path.suffix}")


def _merge_meshes(meshes: Iterable[trimesh.Trimesh]) -> trimesh.Trimesh:
    meshes = list(meshes)
    if not meshes:
        raise ValueError("No mesh components remain after reduction.")
    if len(meshes) == 1:
        return meshes[0].copy()
    return trimesh.util.concatenate(meshes)


def _binary_mask(image: np.ndarray, *, threshold: float = 250.0) -> np.ndarray:
    grayscale = image[..., :3].mean(axis=2)
    return grayscale < threshold


def _views_within_threshold(
    baseline: Dict[str, np.ndarray],
    candidate: Dict[str, np.ndarray],
    threshold: float,
) -> bool:
    for name in baseline:
        base_mask = _binary_mask(baseline[name])
        candidate_mask = _binary_mask(candidate[name])
        difference_ratio = np.count_nonzero(base_mask != candidate_mask) / base_mask.size
        if difference_ratio > threshold:
            return False
    return True


def _component_centroid(component: trimesh.Trimesh) -> np.ndarray:
    return component.bounding_box.centroid


def _components_center(components: Iterable[trimesh.Trimesh]) -> np.ndarray:
    centroids = [_component_centroid(component) for component in components]
    return np.mean(centroids, axis=0)


def _split_mesh(mesh: trimesh.Trimesh) -> Iterable[trimesh.Trimesh]:
    try:
        return mesh.split(only_watertight=False)
    except ImportError as exc:
        raise ImportError(
            "trimesh requires a graph engine such as `networkx` or `scipy` "
            "to split meshes. Install one (for example, via `pip install "
            "trimesh[all]` or `pip install networkx scipy`) and retry."
        ) from exc


def reduce_geometry(
    mesh: trimesh.Trimesh,
    clearance: float = CLEARANCE,
    *,
    image_size: int = DEFAULT_IMAGE_SIZE,
    difference_threshold: float = DIFFERENCE_THRESHOLD,
) -> Tuple[trimesh.Trimesh, int, int]:
    """Remove components that do not affect the rendered anamorphic views.

    Components are first filtered by clearance above the ground plane. Remaining
    solids are then considered one at a time—starting with the component farthest
    from the current center of mass—and removed if their absence does not
    meaningfully alter the three rendered text silhouettes.

    Args:
        mesh: Source mesh containing one or more connected components.
        clearance: Distance above the ground plane that is treated as floating.
        image_size: Size in pixels of the rendered comparisons.
        difference_threshold: Maximum ratio of differing pixels allowed before a
            removal is rejected.

    Returns:
        A tuple containing the reduced mesh, the number of kept components, and
        the number of removed components.
    """

    ground_level = float(mesh.vertices[:, 2].min())
    components = list(_split_mesh(mesh))

    kept_components = []
    removed_by_clearance = 0

    for component in components:
        min_z = float(component.vertices[:, 2].min())
        if min_z <= ground_level + clearance:
            kept_components.append(component)
        else:
            removed_by_clearance += 1

    if not kept_components:
        raise ValueError("All components were removed by clearance filtering.")

    kept_flags = [True] * len(kept_components)
    considered_flags = [False] * len(kept_components)

    current_mesh = _merge_meshes(kept_components)
    current_views = render_views(current_mesh, size=image_size)

    while not all(considered_flags[i] or not kept_flags[i] for i in range(len(kept_components))):
        active_components = [comp for keep, comp in zip(kept_flags, kept_components) if keep]
        center = _components_center(active_components)

        farthest_idx = None
        farthest_distance = -np.inf
        for idx, (keep, considered, component) in enumerate(
            zip(kept_flags, considered_flags, kept_components)
        ):
            if not keep or considered:
                continue
            distance = np.linalg.norm(_component_centroid(component) - center)
            if distance > farthest_distance:
                farthest_distance = distance
                farthest_idx = idx

        if farthest_idx is None:
            break

        candidate_flags = kept_flags.copy()
        candidate_flags[farthest_idx] = False
        candidate_meshes = [comp for keep, comp in zip(candidate_flags, kept_components) if keep]
        if not candidate_meshes:
            considered_flags[farthest_idx] = True
            continue
        candidate_mesh = _merge_meshes(candidate_meshes)
        candidate_views = render_views(candidate_mesh, size=image_size)

        if _views_within_threshold(current_views, candidate_views, difference_threshold):
            kept_flags = candidate_flags
            current_views = candidate_views

        considered_flags[farthest_idx] = True

    reduced_meshes = [comp for keep, comp in zip(kept_flags, kept_components) if keep]
    reduced_mesh = _merge_meshes(reduced_meshes)

    kept_count = len(reduced_meshes)
    removed_count = removed_by_clearance + (len(kept_components) - kept_count)
    return reduced_mesh, kept_count, removed_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reduce an STL by removing components wholly above the letter baseline "
            "and solids that do not impact the rendered anamorphic views."
        )
    )
    parser.add_argument("input", type=Path, help="Path to the source STL file")
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to write the reduced STL (defaults to <input>_reduced.stl)",
    )
    parser.add_argument(
        "--clearance",
        type=float,
        default=CLEARANCE,
        help="Minimum distance above the ground plane to treat as floating",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=DEFAULT_IMAGE_SIZE,
        help="Square image size in pixels for render comparisons",
    )
    parser.add_argument(
        "--difference-threshold",
        type=float,
        default=DIFFERENCE_THRESHOLD,
        help="Maximum fraction of differing pixels allowed when comparing renders",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    mesh = trimesh.load_mesh(args.input, file_type="stl")
    reduced_mesh, kept_count, removed_count = reduce_geometry(
        mesh,
        clearance=args.clearance,
        image_size=args.image_size,
        difference_threshold=args.difference_threshold,
    )

    output_path = args.output or _default_output_path(args.input)
    reduced_mesh.export(output_path)

    print(
        "Removed",
        f" {removed_count} component(s) after clearance and view checks;",
        f" kept {kept_count}. Saved to {output_path}"
    )


if __name__ == "__main__":
    main()
