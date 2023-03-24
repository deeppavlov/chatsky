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
from dff.utils.viewer import make_image
from dff.utils.testing import toy_script

make_image([f"--entry_point={toy_script.__file__}", "--output_file=plot.png"])
