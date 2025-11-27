"""
Reduce an STL by removing floating components above the letter baseline.
"""

import argparse
from pathlib import Path
from typing import Iterable, Tuple

import trimesh

CLEARANCE = 0.01  # Distance above the ground plane used to remove components.


def _default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_reduced{input_path.suffix}")


def _merge_meshes(meshes: Iterable[trimesh.Trimesh]) -> trimesh.Trimesh:
    meshes = list(meshes)
    if not meshes:
        raise ValueError("No mesh components remain after reduction.")
    if len(meshes) == 1:
        return meshes[0].copy()
    return trimesh.util.concatenate(meshes)


def reduce_geometry(
    mesh: trimesh.Trimesh, clearance: float = CLEARANCE
) -> Tuple[trimesh.Trimesh, int, int]:
    """Remove components whose lowest point is above the ground plane.

    Args:
        mesh: Source mesh containing one or more connected components.
        clearance: Distance above the ground plane that is treated as floating.

    Returns:
        A tuple containing the reduced mesh, the number of kept components,
        and the number of removed components.
    """

    ground_level = float(mesh.vertices[:, 2].min())
    try:
        components = mesh.split(only_watertight=False)
    except ImportError as exc:
        raise ImportError(
            "trimesh requires a graph engine such as `networkx` or `scipy` "
            "to split meshes. Install one (for example, via `pip install "
            "trimesh[all]` or `pip install networkx scipy`) and retry."
        ) from exc

    kept_components = []
    removed_count = 0

    for component in components:
        min_z = float(component.vertices[:, 2].min())
        if min_z <= ground_level + clearance:
            kept_components.append(component)
        else:
            removed_count += 1

    reduced_mesh = _merge_meshes(kept_components)
    return reduced_mesh, len(kept_components), removed_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reduce an STL by removing components wholly above the letter baseline."
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    mesh = trimesh.load_mesh(args.input, file_type="stl")
    reduced_mesh, kept_count, removed_count = reduce_geometry(
        mesh, clearance=args.clearance
    )

    output_path = args.output or _default_output_path(args.input)
    reduced_mesh.export(output_path)

    print(
        "Removed"
        f" {removed_count} component(s) above the ground plane;"
        f" kept {kept_count}. Saved to {output_path}"
    )


if __name__ == "__main__":
    main()
