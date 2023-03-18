import difflib
from io import BytesIO
from base64 import b64encode
from pathlib import Path
import re

import plotly.graph_objects as go
from dff.script.utils.script_viewer import graph
from dff.script.utils.script_viewer import plot
from tests.utils import get_path_from_tests_to_current_dir

import pytest


@pytest.fixture(scope="session")
def testing_graph():
    example_dir = Path(f"examples/{get_path_from_tests_to_current_dir(__file__)}") / "python_files"
    G = graph.get_graph(example_dir / "main.py", example_dir)
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
    ["params", "reference_file"],
    [
        (
            dict(
                show_misc=False,
                show_response=False,
                show_global=False,
                show_local=False,
                show_isolates=False,
                random_seed=1,
            ),
            Path(__file__).parent / "opts_off.dot",
        ),
        (
            dict(
                show_misc=True, show_response=True, show_global=True, show_local=True, show_isolates=True, random_seed=1
            ),
            Path(__file__).parent / "opts_on.dot",
        ),
    ],
)
def test_plotting_2(params, reference_file, testing_graph, tmp_path):
    testing_plot = plot.get_plot(testing_graph, **params)
    plot_file = tmp_path / "plot"
    testing_plot.render(filename=plot_file)
    test_lines = plot_file.open().readlines()
    reference_lines = reference_file.open().readlines()
    diff = difflib.unified_diff(test_lines, reference_lines)
    assert len(list(diff)) == 0
