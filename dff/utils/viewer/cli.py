import logging
from pathlib import Path
import argparse

from .graph import get_graph
from .plot import get_plot
from .app import create_app
from .image import make_image


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
    "-rf",
    "--root_file",
    required=True,
    metavar="ROOT_FILE",
    help="Python file to start parsing with",
    type=is_file,
)
py2file_parser.add_argument(
    "-d",
    "--project_root_dir",
    required=True,
    metavar="PROJECT_ROOT_DIR",
    help="Directory that contains all the local files required to run ROOT_FILE",
    type=is_dir,
)
py2file_parser.add_argument(
    "-rq",
    "--requirements",
    metavar="REQUIREMENTS",
    help="File with project requirements to override those collected by parser",
    type=is_file,
    required=False,
    default=None,
)
py2file_parser.add_argument("-r", "--show_response", action="store_true", help="Show node response values.")
py2file_parser.add_argument("-m", "--show_misc", action="store_true", help="Show node misc values.")
py2file_parser.add_argument("-l", "--show_local", action="store_true", help="Show local transitions.")
py2file_parser.add_argument("-g", "--show_global", action="store_true", help="Show global transitions.")
py2file_parser.add_argument("-i", "--show_isolates", action="store_true", help="Show isolated nodes.")
py2file_parser.add_argument(
    "-rs", "--random_seed", required=False, type=int, default=1, help="Random seed to control color generation."
)

server_parser = argparse.ArgumentParser(add_help=False)
server_parser.add_argument(
    "-H", "--host", required=False, metavar="HOST", type=str, default="127.0.0.1", help="Dash application host."
)
server_parser.add_argument(
    "-p", "--port", required=False, metavar="PORT", type=int, default=5000, help="Dash application port."
)


def make_server():
    server_praser = argparse.ArgumentParser(parents=[py2file_parser, server_parser], add_help=True)
    args: argparse.Namespace = server_praser.parse_args()
    graph = get_graph(**vars(args))
    plot = get_plot(graph, **vars(args))
    app = create_app(plot)
    app.run(host=args.host, port=args.port, debug=True, dev_tools_hot_reload=True)


def make_image():
    image_parser = argparse.ArgumentParser(parents=[py2file_parser], add_help=True)
    image_parser.add_argument(
        "-f",
        "--format",
        metavar="FORMAT",
        help="Graphviz output format",
        default="png",
        choices=["png", "jpeg", "svg", "gif", "bmp", "dot"],
        type=str,
    )
    image_parser.add_argument(
        "-o",
        "--output_file",
        metavar="OUTPUT_FILE",
        help="Image file",
        type=str,
    )
    args: argparse.Namespace = image_parser.parse_args()
    graph = get_graph(**vars(args))
    plot = get_plot(graph, **vars(args))
    make_image(plot, args.output_file, format=args.format)
