from typing import Union
from pathlib import Path

import networkx as nx

from dff.utils.parser.dff_project import DFFProject


def get_graph(entry_point: Union[str, Path], project_root_dir: Union[str, Path, None] = None) -> nx.Graph:
    if not isinstance(entry_point, Path):
        entry_point = Path(entry_point)
    project_root_dir = project_root_dir or entry_point.parent.absolute()
    project: DFFProject = DFFProject.from_python(project_root_dir=project_root_dir, entry_point=entry_point.absolute())
    return project.graph
