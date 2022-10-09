from pathlib import Path
import argparse

from .graph import get_graph
from .plot import get_plot
from .app import create_app
from .image import create_image


def is_dir(arg: str) -> Path:
    """Check that the passed argument is a directory

    :param arg: Argument to check
    :type arg: str
    :return: :py:class:`.Path` instance created from arg if it is a directory
    """
    path = Path(arg)
    if path.is_dir():
        return path
    raise argparse.ArgumentTypeError(f"Not a directory: {path}")


def is_file(arg: str) -> Path:
    """Check that the passed argument is a file

    :param arg: Argument to check
    :type arg: str
    :return: :py:class:`.Path` instance created from arg if it is a file
    """
    path = Path(arg)
    if path.is_file():
        return path
    raise argparse.ArgumentTypeError(f"Not a file: {path}")


py2file_parser = argparse.ArgumentParser(add_help=False)
py2file_parser.add_argument(
    "root_file",
    metavar="ROOT_FILE",
    help="Python file to start parsing with",
    type=is_file,
)
py2file_parser.add_argument(
    "project_root_dir",
    metavar="PROJECT_ROOT_DIR",
    help="Directory that contains all the local files required to run ROOT_FILE",
    type=is_dir,
)
py2file_parser.add_argument(
    "--requirements",
    metavar="REQUIREMENTS",
    help="File with project requirements to override those collected by parser",
    type=is_file,
    required=False,
    default=None,
)


def make_server():
    server_praser = argparse.ArgumentParser(parents=[py2file_parser], add_help=True)
    args: argparse.Namespace = server_praser.parse_args()
    graph = get_graph(**vars(args))
    plot = get_plot(graph)
    app = create_app(plot)
    app.run(debug=True, dev_tools_hot_reload=True)


def make_image():
    image_parser = argparse.ArgumentParser(parents=[py2file_parser], add_help=True)
    image_parser.add_argument(
        "output_file",
        metavar="OUTPUT_FILE",
        help="File to store parser output in",
        type=str,
    )
    args: argparse.Namespace = image_parser.parse_args()
    graph = get_graph(**vars(args))
    plot = get_plot(graph)
    create_image(plot, args.output_file)
