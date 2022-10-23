from io import BytesIO
from base64 import b64encode
from pathlib import Path

import plotly.graph_objects as go
from df_script_viewer import graph
from df_script_viewer import plot

import pytest


@pytest.fixture
def testing_graph():
    dir = Path(__file__).parent.parent / "examples" / "python_files"
    G = graph.get_graph(dir / "main.py", dir)
    yield G


@pytest.mark.parametrize(["params"], [{}, {}])
def test_plotting(params, testing_graph):
    testing_plot = plot.get_plot(testing_graph)
    _bytes = testing_plot.pipe("png")
    assert isinstance(_bytes, bytes) and len(_bytes) > 0
    prefix = "data:image/png;base64,"
    with BytesIO(_bytes) as stream:
        base64 = prefix + b64encode(stream.getvalue()).decode("utf-8")
    fig = go.Figure(go.Image(source=base64))
    assert fig


@pytest.mark.parametrize(["params"], [{}, {}])
def test_plotting_2(testing_graph, tmp_path):
    testing_plot = plot.get_plot(testing_graph)
    plot_file = str(tmp_path / "plot")
    testing_plot.render(filename=plot_file)
    with open(plot_file, "r", encoding="utf-8") as file:
        text = file.read()
    lines = text.splitlines()
