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
# Installs dff with dependencies for running examples
# To install the minimal version of dff, use `pip install dff`
# To install other options of dff, use `pip install dff[OPTION_NAME1,OPTION_NAME2]` 
# where OPTION_NAME can be one of the options from EXTRA_DEPENDENCIES.
# e.g `pip install dff[ydb, mysql]` installs dff with dependencies for using Yandex Database and MySQL
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
