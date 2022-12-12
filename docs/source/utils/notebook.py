from jupytext import jupytext


def add_installation_cell_into_py(s: str):
    return jupytext.reads(
        f"""# %% [markdown]
### Installing dependencies

# %%
!python3 -m pip install -q dff[examples]


{s}
""",
        "py:percent",
    )
