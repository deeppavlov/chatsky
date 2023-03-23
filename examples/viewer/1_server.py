# %% [markdown]
"""
# 1. Cache

"""
# %% [markdown]
"""
## View the graph on a Dash server

"""
# %% [markdown]
"""
```bash
dff.viewer.server -e "./python_files/main.py" -d "./python_files/" -H localhost -P 8000
```
"""
# %% [markdown]
"""
## CLI parameters reference
"""
# %% [markdown]
"""
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
#