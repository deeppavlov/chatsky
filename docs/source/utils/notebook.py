from jupytext import jupytext


def insert_installation_cell_into_py_example():
    def inner(example_text: str):
        second_cell = example_text.find("\n# %%", 5)
        return jupytext.reads(
            f"""{example_text[:second_cell]}

# %% [markdown]
\"\"\"
__Installing dependencies__
\"\"\"

# %%
!python3 -m pip install -q dff[examples]

# %% [markdown]
\"\"\"
__Running example__
\"\"\"

{example_text[second_cell:]}
""",
            "py:percent",
        )

    return inner
