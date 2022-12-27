import re

from jupytext import jupytext

second_cell = re.compile(r'# %%\n')


def insert_installation_cell_into_py_example():

    def inner(example_text: str):
        match = second_cell.search(example_text)
        return jupytext.reads(
            f"""{example_text[: match.span()[0]]}

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

{example_text[match.span()[0] :]}
""",
            "py:percent",
        )

    return inner
