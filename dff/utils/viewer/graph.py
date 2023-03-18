from typing import Union
from pathlib import Path

import networkx as nx

from dff.utils.parser.dff_project import DFFProject


def get_graph(root_file: Union[str, Path]) -> nx.Graph:
    if not isinstance(root_file, Path):
        root_file = Path(root_file)
    project: DFFProject = DFFProject.from_python(
        project_root_dir=root_file.parent.absolute(), entry_point=root_file.absolute()
    )
    return project.graph
