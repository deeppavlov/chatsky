# %% [markdown]
"""
# 1. Server

## View the graph on a Dash server

```bash
dff.viewer.server -e "./python_files/main.py" -d "./python_files/" -H localhost -P 8000
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
--host: Dash application host.
--port: Dash application port.

"""
# %%
from pathlib import Path
import sys
from dff.utils.viewer import make_server
from dff.utils.testing.common import is_interactive_mode

if is_interactive_mode():
    entry_point = "../../tests/viewer/TEST_CASES/main.py"
else:
    entry_point = Path(__file__).parent.parent / "tests" / "viewer" / "TEST_CASES" / "main.py"

sys.argv = ["", f"--entry_point={entry_point}"]
make_server(sys.argv[1:])
