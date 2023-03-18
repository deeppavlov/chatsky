# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# flake8: noqa

# %% [markdown]
# **_Note:_** examples here use the python interface of the parser but it's identical to parser's cli

# %%
import dff.script.import_export.parser
from pathlib import Path
from tempfile import mkdtemp

# %%
example_dir = Path(mkdtemp())

# %% [markdown]
# ## 1. Basic examples

# %% [markdown]
# This basic example shows that parser can extract imports, dictionaries, function calls.

# %%
working_dir = example_dir / "basic_example"
working_dir.mkdir()
main_file = working_dir / "main.py"
main_file.touch()
yaml_file = working_dir / "script.yaml"

# %%
with open(main_file, "w") as main:
    main.write(
        """
from pathlib import Path
import dff.core.engine as dfe
import mypackage

dictionary = {
    1: Path,
    2: dfe,
    3: {4: mypackage},
    4: "text",
}

result = this_function_does_not_exist(dictionary)
    """
    )

dff.script.import_export.parser.py2yaml(
    root_file=main_file, project_root_dir=working_dir, output_file=yaml_file
)

with open(yaml_file, "r") as out:
    print(out.read())

# %%
dff.script.import_export.parser.yaml2py(yaml_file=yaml_file, extract_to_directory=working_dir)

with open(main_file, "r") as out:
    print(out.read())

# %% [markdown]
# ## 2. Str tag

# %% [markdown]
# As you can see in a previous example both dictionary values ``Path`` and ``text`` are written in plain text. How did ``yaml2py`` parser figure out that it needs to put quotations around ``text``? Parser checks every plain text on whether it could be a correct line of python code. If it isn't parser knows that it's a string.
#
# But what if you want to use a string that is also a correct line of python code? That's where ``!str`` tag comes in:

# %%
working_dir = example_dir / "str_tag"
working_dir.mkdir()
main_file = working_dir / "main.py"
main_file.touch()
yaml_file = working_dir / "script.yaml"

# %%
with open(main_file, "w") as main:
    main.write(
        """
from pathlib import Path

dictionary = {
    1: Path,
    2: "Path",
    3: print,
    4: "print",
    5: printd,
    6: "printd"
}

    """
    )

dff.script.import_export.parser.py2yaml(
    root_file=main_file, project_root_dir=working_dir, output_file=yaml_file
)

with open(yaml_file, "r") as out:
    print(out.read())

# %%
dff.script.import_export.parser.yaml2py(yaml_file=yaml_file, extract_to_directory=working_dir)

with open(main_file, "r") as out:
    print(out.read())

# %% [markdown]
# if you want to specify if the parser should treat a value as a string or as a python line of code you could use tags ``!str`` or ``!py`` respectively.

# %% [markdown]
# ## 3. Recursive parsing

# %% [markdown]
# If your projects contains several modules that are imported in your ``root_file`` they will be parsed as well:

# %%
working_dir = example_dir / "recursive_parsing"
working_dir.mkdir()
python_files = working_dir / "python_files"
python_files.mkdir()
main_file = python_files / "main.py"
main_file.touch()

some_package = python_files / "some_package"
some_package.mkdir()
(some_package / "__init__.py").touch()
another_file = some_package / "another_file.py"
another_file.touch()
unparsed = python_files / "unparsed.py"
unparsed.touch()
yaml_file = working_dir / "script.yaml"

# %% [markdown]
# The project has the following structure:
#
# ``
# +-- python_files``
#
# ``
# +--++-- main.py``
#
# ``
# +--++-- some_package``
#
# ``
# +--++--++-- another_file.py``
#
# ``
# +--++-- unparsed.py``
#

# %%
with open(main_file, "w") as main:
    main.write(
        """
from some_package import another_file
from some_package.another_file import something, something_else
import unparsed

dictionary = {
    1: something,
    2: something_else,
    3: unparsed.path
}

    """
    )

with open(another_file, "w") as file:
    file.write(
        """
import abc as something

    """
    )

with open(unparsed, "w") as file:
    file.write(
        """
from pathlib import Path as path

print(path)

    """
    )

dff.script.import_export.parser.py2yaml(
    root_file=main_file, project_root_dir=python_files, output_file=yaml_file
)

with open(yaml_file, "r") as out:
    print(out.read())

# %% [markdown]
# As you can see ``unparsed.py`` wasn't parsed as it doesn't follow the parser structure rules described in [README.md](../README.md). Replacing ``print(path)`` with ``some_variable = print(path)`` will fix that issue.

# %% [markdown]
# **_Note:_** If ``project_root_dir`` contains ``__init__.py`` file ``yaml2py`` parser will put all the files inside a new directory with the same name as ``project_root_dir`` inside ``extract_to_directory``. So the result will be:
#
# ``
# +-- extract_to_directory``
#
# ``
# +--++-- project_root_dir``
#
# ``
# +--++--++-- __init__.py``
#
# ``
# +--++--++-- ...``
#

# %% [markdown]
# ## 4. Actor arg checking

# %% [markdown]
# If your script contains a call to ``dff.core.engine.core.Actor`` or ``dff.core.engine.core.actor.Actor`` the arguments of that call will be checked.

# %%
working_dir = example_dir / "act_arg"
working_dir.mkdir()
main_file = working_dir / "main.py"
main_file.touch()
yaml_file = working_dir / "script.yaml"

# %% [markdown]
# So this works fine:

# %%
with open(main_file, "w") as main:
    main.write(
        """
from dff.core.engine.core import Actor as act
import dff.core.engine.core.keywords as kw

actor = act(
    {"flow": {"node": {kw.RESPONSE: "hey"}}},
    ("flow", "node")
)

    """
    )

dff.script.import_export.parser.py2yaml(
    root_file=main_file, project_root_dir=working_dir, output_file=yaml_file
)

with open(yaml_file, "r") as out:
    print(out.read())

# %% [markdown]
# While this fails:

# %%
try:
    with open(main_file, "w") as main:
        main.write(
            """
from dff.core.engine.core import Actor as act
import dff.core.engine.core.keywords as kw

script = {"flow": {"node": {kw.response: "hey"}}}

actor = act(
    start_label=("flow", "node"),
    script=script
)

        """
        )

    dff.script.import_export.parser.py2yaml(
        root_file=main_file, project_root_dir=working_dir, output_file=yaml_file
    )

    with open(yaml_file, "r") as out:
        print(out.read())
except Exception as error:
    print(type(error), error)

# %% [markdown]
# **_Note:_** Actor argument checking works with recursive parsing.

# %% [markdown]
# ## 5. Export as graph

# %%
working_dir = example_dir / "graph_export"
working_dir.mkdir()
main_file = working_dir / "main.py"
main_file.touch()
output_file = working_dir / "graph.json"

# %%
with open(main_file, "w") as main:
    main.write(
        """
from dff.core.engine.core import Actor as act
import dff.core.engine.core.keywords as kw
import dff.core.engine.conditions as cnd

actor = act(
    {
        "flow1": {
            "node": {
                kw.RESPONSE: "hey",
                kw.TRANSITIONS: {
                    ("flow2", "node"): cnd.true()
                }
            }
        },
        "flow2": {
            "node": {
                kw.RESPONSE: "hi",
                kw.TRANSITIONS: {
                    ("flow1", "node"): cnd.true()
                }
            }
        }
    },
    ("flow1", "node")
)

    """
    )

# %%
dff.script.import_export.parser.py2graph(
    root_file=main_file, project_root_dir=working_dir, output_file=output_file
)

# %%
import networkx as nx
import json

with open(output_file, "r") as data:
    graph = nx.node_link_graph(json.load(data), True, True)

# %%
nx.draw_networkx(graph, font_size=6)

# %% [markdown]
# **_Note:_** labels from ``dff.core.engine.core.labels`` such as ``dff.core.engine.core.labels.repeat`` are not yet supported and edges that use them refer to a node ``("NONE", )`` instead.
