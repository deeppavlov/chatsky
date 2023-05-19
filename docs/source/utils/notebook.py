from jupytext import jupytext


def get_extra_deps_line_number():
    """This function finds the line number of the EXTRA_DEPENDENCIES variable in the setup.py file."""
    with open("setup.py", "r", encoding="utf-8") as setup:
        return setup.readlines().index("EXTRA_DEPENDENCIES = {\n") + 1


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
\"\"\"

# %%
!python3 -m pip install -q dff[full,tests]
# Installs dff with dependencies for running tutorials
# To install the minimal version of dff, use `pip install dff`
# To install other options of dff, use `pip install dff[OPTION_NAME1,OPTION_NAME2]`
# where OPTION_NAME can be one of the options from EXTRA_DEPENDENCIES.
# e.g `pip install dff[ydb, mysql]` installs dff with dependencies for using Yandex Database and MySQL
# EXTRA_DEPENDENCIES can be found in
# https://github.com/deeppavlov/dialog_flow_framework/blob/dev/setup.py#L{get_extra_deps_line_number()}


# %% [markdown]
\"\"\"
__Running tutorial__
\"\"\"

{tutorial_text[second_cell:]}
""",
            "py:percent",
        )

    return inner
