import re

from jupytext import jupytext

start_pattern = re.compile(r'# %% \[markdown\]\n"""\n# (\d\. .*)\n\n[\S\s]*?"""\n')


def insert_installation_cell_into_py_example():

    def inner(example_text: str):
        match = start_pattern.match(example_text)
        example_title = example_text[: match.span()[1]]
        example_body = example_text[match.span()[1] :]
        return jupytext.reads(
            f"""{example_title}

# %% [markdown]
\"\"\"
__Installing dependencies__
\"\"\"

# %%
!python3 -m pip install -q dff[full]

# %% [markdown]
\"\"\"
__Running example__
\"\"\"

{example_body}
""",
            "py:percent",
        )

    return inner
