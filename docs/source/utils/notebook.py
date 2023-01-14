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
!python3 -m pip install -q dff[examples] # Installs dff with dependencies for running examples
# To install the minimal version of dff, use `pip install dff`
# To install other options of dff, use `pip install dff[OPTION_NAME]`
# where OPTION_NAME can be one of the options from EXTRA_DEPENDENCIES
# EXTRA_DEPENDENCIES can be found in https://github.com/deeppavlov/dialog_flow_framework/blob/dev/setup.py


# %% [markdown]
\"\"\"
__Running example__
\"\"\"

{example_text[second_cell:]}
""",
            "py:percent",
        )

    return inner
