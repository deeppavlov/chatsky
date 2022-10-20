from pathlib import Path

import networkx as nx

from df_script_parser.processors.recursive_parser import RecursiveParser


def get_graph(root_file, project_root_dir, requirements=None, output_file=None) -> nx.Graph:
    project = RecursiveParser(Path(project_root_dir).absolute())
    if requirements:
        with open(requirements, "r", encoding="utf-8") as reqs:
            project.requirements = [x for x in reqs.read().split("\n") if x]    
    project.parse_project_dir(Path(root_file).absolute())

    return project.to_graph()
