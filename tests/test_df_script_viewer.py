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


def test_plotting(testing_graph):
    testing_plot = plot.get_plot(testing_graph)
    assert isinstance(testing_plot, bytes) and len(testing_plot) > 0
    prefix = "data:image/png;base64,"
    with BytesIO(testing_plot) as stream:
        base64 = prefix + b64encode(stream.getvalue()).decode("utf-8")
    fig = go.Figure(go.Image(source=base64))
    assert fig
