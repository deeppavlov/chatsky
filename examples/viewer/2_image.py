# %% [markdown]
"""
# 2. Image

## View the graph as a static image.

```bash
dff.viewer.image -e ./python_files/main.py -d ./python_files/ -o ./plot.png
```

## CLI parameters reference

--entry_point: Python file to start parsing with.
--project_root_dir: Directory that contains all the local files required to run ROOT_FILE.
--show_response: Show node response values.
--show_misc: Show node misc values.
--show_local: Show local transitions.
--show_processing: Show processing functions.
--show_global: Show global transitions.
--show_isolates: Show isolated nodes.
--random_seed: Random seed to control color generation.
--format: Graphviz output format.
--output_file: Image file.

"""
# %%
from pathlib import Path
from dff.utils.viewer import make_image
from dff.utils.testing.common import is_interactive_mode

if is_interactive_mode():
    entry_point = "../../tests/viewer/TEST_CASES/main.py"
else:
    entry_point = Path(__file__).parent.parent / "tests" / "viewer" / "TEST_CASES" / "main.py"

make_image([f"--entry_point={entry_point}", "--output_file=plot.png"])

# %%
