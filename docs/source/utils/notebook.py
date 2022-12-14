import re
from typing import Dict, List, Optional

from jupytext import jupytext

start_pattern = re.compile(r'# %% \[markdown\]\n"""\n# (\d\. .*)\n\n[\S\s]*?"""\n')


def add_installation_cell_into_example(default: str, dependencies: Optional[Dict[str, List[str]]] = None):
    dependencies = dict() if dependencies is None else dependencies

    def inner(example_text: str):
        match = start_pattern.match(example_text)
        example_title = example_text[: match.span()[1]]
        example_body = example_text[match.span()[1] :]
        example_name = match.group(1)
        return jupytext.reads(
            f"""{example_title}

# %% [markdown]
\"\"\"
#### Installing dependencies
\"\"\"

# %%
!python3 -m pip install -q {', '.join(dependencies.get(example_name, [default]))}

# %% [markdown]
\"\"\"
#### Running example
\"\"\"

{example_body}
""",
            "py:percent",
        )

    return inner
