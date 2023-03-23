import difflib
import time
from multiprocessing import Process
from io import BytesIO
from base64 import b64encode
from pathlib import Path

import pytest

try:
    import plotly.graph_objects as go
    from dff.utils.viewer import app
    from dff.utils.viewer import graph
    from dff.utils.viewer import plot
    from dff.utils.viewer import cli
except ImportError:
    pytest.skip(allow_module_level=True, reason="Missing dependencies for dff parser.")


@pytest.fixture(scope="session")
def example_dir():
    example_d = Path(__file__).parent / "TEST_CASES"
    yield example_d


@pytest.fixture(scope="session")
def nx_graph(example_dir):
    G = graph.get_graph(example_dir / "main.py", example_dir.absolute())
    yield G


@pytest.mark.parametrize("show_misc", [True, False])
@pytest.mark.parametrize("show_global", [True, False])
@pytest.mark.parametrize("show_local", [True, False])
@pytest.mark.parametrize("show_isolates", [True, False])
def test_plotting(nx_graph, show_misc, show_global, show_local, show_isolates):
    testing_plot = plot.get_plot(**locals())
    _bytes = testing_plot.pipe("png")
    assert isinstance(_bytes, bytes) and len(_bytes) > 0
    prefix = "data:image/png;base64,"
    with BytesIO(_bytes) as stream:
        base64 = prefix + b64encode(stream.getvalue()).decode("utf-8")
    fig = go.Figure(go.Image(source=base64))
    assert app.create_app(testing_plot)
    assert fig


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
                random_seed=1,
            ),
            Path(__file__).parent / "opts_on.dot",
        ),
    ],
)
def test_plotting_2(params, reference_file, nx_graph, tmp_path):
    testing_plot = plot.get_plot(nx_graph, **params)
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
    args = [*params, '-e', entrypoint, '-d', entrydir, '-H', 'localhost', '-P', '5000']
    process = Process(target=cli.make_server, args=(args,))
    process.start()
    time.sleep(3)
    assert process.is_alive()
    process.kill()
    while process.is_alive():
        time.sleep(0.1)
