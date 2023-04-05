import os
import difflib
import time
from multiprocessing import Process
from pathlib import Path

import pytest

try:
    from dff.utils.viewer import app
    from dff.utils.viewer import graph
    from dff.utils.viewer import graph_plot
    from dff.utils.viewer import cli
    from dff.utils.viewer import preprocessing
    from dff.utils.viewer import utils
except ImportError:
    pytest.skip(allow_module_level=True, reason="Missing dependencies for dff parser.")

dot_exec_result = os.system("which dot")
if dot_exec_result != 0:
    pytest.skip(allow_module_level=True, reason="Graphviz missing from the system.")


@pytest.fixture(scope="session")
def example_dir():
    example_d = Path(__file__).parent / "TEST_CASES"
    yield example_d


@pytest.fixture(scope="function")
def nx_graph(example_dir):
    G = graph.get_graph(example_dir / "main.py", example_dir.absolute())
    yield G


@pytest.mark.parametrize("show_global", [True, False])
@pytest.mark.parametrize("show_local", [True, False])
@pytest.mark.parametrize("show_isolates", [True, False])
@pytest.mark.parametrize("show_unresolved", [True, False])
def test_preprocessing(nx_graph, show_global, show_local, show_isolates, show_unresolved):
    G = preprocessing.preprocess(**locals())
    glob = ("NODE", preprocessing.VIRTUAL_FLOW_KEY, "GLOBAL") in G.nodes
    assert glob == show_global
    unresolved = ("NODE", preprocessing.VIRTUAL_FLOW_KEY, preprocessing.UNRESOLVED_KEY) in G.nodes
    assert unresolved == show_unresolved


@pytest.mark.parametrize("show_misc", [True, False])
@pytest.mark.parametrize("show_response", [True, False])
@pytest.mark.parametrize("show_processing", [True, False])
def test_plotting(nx_graph, show_misc, show_response, show_processing):
    nx_graph = preprocessing.preprocess(**locals())
    testing_plot = graph_plot.get_plot(**locals())
    plotly_fig = utils.graphviz_to_plotly(testing_plot)
    assert app.create_app(plotly_fig)
    assert plotly_fig


@pytest.mark.parametrize(
    ["params", "reference_file"],
    [
        (
            dict(
                show_misc=False,
                show_processing=False,
                show_response=False,
                show_global=False,
                show_local=False,
                show_isolates=False,
                show_unresolved=False,
                random_seed=1,
            ),
            Path(__file__).parent / "opts_off.dot",
        ),
        (
            dict(
                show_misc=True,
                show_processing=True,
                show_response=True,
                show_global=True,
                show_local=True,
                show_isolates=True,
                show_unresolved=True,
                random_seed=1,
            ),
            Path(__file__).parent / "opts_on.dot",
        ),
    ],
)
def test_plotting_2(nx_graph, params, reference_file, tmp_path):
    nx_graph = preprocessing.preprocess(nx_graph, **params)
    testing_plot = graph_plot.get_plot(nx_graph, **params)
    plot_file = tmp_path / "plot"
    testing_plot.render(filename=plot_file)
    test_lines = plot_file.open().readlines()
    reference_lines = reference_file.open().readlines()
    diff = difflib.unified_diff(test_lines, reference_lines)
    assert len(list(diff)) == 0


@pytest.mark.parametrize(
    ["params", "reference_file"],
    [
        (
            [
                "--random_seed=1",
            ],
            Path(__file__).parent / "opts_off.dot",
        ),
        (
            [
                "--show_misc",
                "--show_processing",
                "--show_response",
                "--show_global",
                "--show_local",
                "--show_isolates",
                "--show_unresolved",
                "--random_seed=1",
            ],
            Path(__file__).parent / "opts_on.dot",
        ),
    ],
)
def test_image_cli(params, example_dir, reference_file, tmp_path):
    plot_file = str((tmp_path / "plot").absolute())
    entrypoint, entrydir = str((example_dir / "main.py").absolute()), str(example_dir.absolute())
    cli.make_image(
        args=[
            *params,
            f"--entry_point={entrypoint}",
            f"--project_root_dir={entrydir}",
            "-f",
            "dot",
            "-o",
            f"{plot_file}",
        ]
    )
    test_lines = Path(plot_file).open().readlines()
    reference_lines = reference_file.open().readlines()
    diff = difflib.unified_diff(test_lines, reference_lines)
    assert len(list(diff)) == 0


@pytest.mark.parametrize(
    ["params"],
    [
        (
            [
                "--random_seed=1",
            ],
        ),
        (
            [
                "--show_misc",
                "--show_processing",
                "--show_response",
                "--show_global",
                "--show_local",
                "--show_isolates",
                "--random_seed=1",
            ],
        ),
    ],
)
def test_server_cli(params, example_dir):
    entrypoint, entrydir = str((example_dir / "main.py").absolute()), str(example_dir.absolute())
    args = [*params, "-e", entrypoint, "-d", entrydir, "-H", "localhost", "-P", "5000"]
    process = Process(target=cli.make_server, args=(args,))
    process.start()
    time.sleep(3)
    assert process.is_alive()
    process.kill()
    while process.is_alive():
        time.sleep(0.1)
