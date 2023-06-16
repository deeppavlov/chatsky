from jupytext import jupytext


def insert_installation_cell_into_py_tutorial():
    """
    This function modifies a Jupyter notebook by inserting a code cell for installing 'dff' package
    and its dependencies, and a markdown cell with instructions for the user. It uses the location of
    the second cell in the notebook as a reference point to insert the new cells.
    """

    def inner(tutorial_text: str):
        second_cell = tutorial_text.find("\n# %%", 5)
        return jupytext.reads(
            f"""{tutorial_text[:second_cell]}

# %% [markdown]
\"\"\"
__Installing dependencies__

The cell below installs dff with dependencies for running tutorials
To install the minimal version of dff, use `pip install dff`
To install other options of dff, use `pip install dff[OPTION_NAME1,OPTION_NAME2]`
where OPTION_NAME can be one of the options from EXTRA_DEPENDENCIES.
e.g `pip install dff[ydb, mysql]` installs dff with dependencies for using Yandex Database and MySQL
EXTRA_DEPENDENCIES can be found in
[here](https://github.com/deeppavlov/dialog_flow_framework/blob/dev/README.md#installation)
\"\"\"

# %%
!python3 -m pip install -q dff[tutorials]

{tutorial_text[second_cell:]}
""",
            "py:percent",
        )

    return inner
