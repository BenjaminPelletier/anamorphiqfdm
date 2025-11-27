# anamorphiqfdm

## Generating the three-angle text intersection mesh

Use `generate_anamorphic_mesh.py` to create an STL mesh whose silhouette reveals three
different strings depending on the viewing angle. The script extrudes 1-unit-tall text on
front, 45° left, and 45° right planes, with extrusion distance based on the longest string,
intersects the three solids, and writes the result to STL.

```bash
python generate_anamorphic_mesh.py "FRONT" "LEFT" "RIGHT" --font "Arial" --output mesh.stl
```

The `--font` parameter accepts any CadQuery-supported font name or path.

### Running with uv

This repository ships a `pyproject.toml` describing the CadQuery dependency so you can run
the script directly with [`uv`](https://docs.astral.sh/uv/). The following command will
create and reuse a virtual environment, install CadQuery, and execute the script in a
single step:

```bash
uv run generate_anamorphic_mesh.py "FRONT" "LEFT" "RIGHT" --font "Arial" --output mesh.stl
```

CadQuery currently supports Python up to 3.13, so ensure the selected interpreter is
below 3.14 when running with `uv`.

## Rendering orthographic views of the STL

Use `render_anamorphic_views.py` to load the generated STL with `trimesh` and write
three orthographic PNG renders that match the front, 45° left, and 45° right
viewing planes used to create the model:

```bash
python render_anamorphic_views.py mesh.stl --output-dir renders --size 1024
```
