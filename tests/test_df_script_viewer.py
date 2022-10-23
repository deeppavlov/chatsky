from io import BytesIO
from base64 import b64encode
from pathlib import Path
import re

import plotly.graph_objects as go
from df_script_viewer import graph
from df_script_viewer import plot

import pytest


@pytest.fixture(scope="session")
def testing_graph():
    dir = Path(__file__).parent.parent / "examples" / "python_files"
    G = graph.get_graph(dir / "main.py", dir)
    yield G


@pytest.mark.parametrize(
    ["params"],
    [
        (dict(show_misc=False, show_response=False, show_global=False, show_local=False, show_isolates=False),),
        (dict(show_misc=True, show_response=True, show_global=True, show_local=True, show_isolates=True),),
    ],
)
def test_plotting(params, testing_graph):
    testing_plot = plot.get_plot(testing_graph, **params)
    _bytes = testing_plot.pipe("png")
    assert isinstance(_bytes, bytes) and len(_bytes) > 0
    prefix = "data:image/png;base64,"
    with BytesIO(_bytes) as stream:
        base64 = prefix + b64encode(stream.getvalue()).decode("utf-8")
    fig = go.Figure(go.Image(source=base64))
    assert fig


@pytest.mark.parametrize(
    ["params", "num_nodes", "num_flows"],
    [
        (dict(show_misc=False, show_response=False, show_global=False, show_local=False, show_isolates=False), 11, 4),
        (dict(show_misc=True, show_response=True, show_global=True, show_local=True, show_isolates=True), 13, 4),
    ],
)
def test_plotting_2(params, num_nodes, num_flows, testing_graph, tmp_path):
    testing_plot = plot.get_plot(testing_graph, **params)
    plot_file = str(tmp_path / "plot")
    testing_plot.render(filename=plot_file)
    with open(plot_file, "r", encoding="utf-8") as file:
        text = file.read()
    assert len(re.findall(r"table", text)) == num_nodes * 2
    assert len(re.findall(r"subgraph", text)) == num_flows
