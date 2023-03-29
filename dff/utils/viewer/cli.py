import sys
from pathlib import Path
from typing import Optional
import argparse

import hupper

from . import graph_plot
from . import chord_plot
from . import image
from .graph import get_graph
from .app import create_app
from .preprocessing import preprocess
from .utils import graphviz_to_plotly


def is_dir(arg: Optional[str]) -> Optional[Path]:
    """Check that the passed argument is a directory

    :param arg: Argument to check
    :return: :py:class:`.Path` instance created from arg if it is a directory
    """
    if arg is None:
        return arg
    elif isinstance(arg, str):
        path = Path(arg)
        if path.is_dir():
            return path
    raise argparse.ArgumentTypeError(f"Not a directory: {path}")


def is_file(arg: str) -> Path:
    """Check that the passed argument is a file

    :param arg: Argument to check
    :return: :py:class:`.Path` instance created from arg if it is a file
    """
    path = Path(arg)
    if path.is_file():
        return path
    raise argparse.ArgumentTypeError(f"Not a file: {path}")


py2file_parser = argparse.ArgumentParser(add_help=False)
py2file_parser.add_argument(
    "-e",
    "--entry_point",
    required=True,
    metavar="ENTRY_POINT",
    help="Python file to start parsing with",
    type=is_file,
)
py2file_parser.add_argument(
    "-d",
    "--project_root_dir",
    metavar="PROJECT_ROOT_DIR",
    help="Directory that contains all the local files required to run ROOT_FILE",
    type=is_dir,
)
py2file_parser.add_argument(
    "-t",
    "--type",
    choices=["graph", "chord"],
    default="graph",
    help="Plot type: graph plot or chord plot.",
)
py2file_parser.add_argument(
    "-r", "--show_response", "--show-response", action="store_true", help="Show node response values."
)
py2file_parser.add_argument("-m", "--show_misc", "--show-misc", action="store_true", help="Show node misc values.")
py2file_parser.add_argument("-l", "--show_local", "--show-local", action="store_true", help="Show local transitions.")
py2file_parser.add_argument(
    "-p", "--show_processing", "--show-processing", action="store_true", help="Show processing functions."
)
py2file_parser.add_argument(
    "-g", "--show_global", "--show-global", action="store_true", help="Show global transitions."
)
py2file_parser.add_argument(
    "-i", "--show_isolates", "--show-isolates", action="store_true", help="Show isolated nodes."
)
py2file_parser.add_argument(
    "-u", "--show_unresolved", "--show-unresolved", action="store_true", help="Show unresolved transitions"
)
py2file_parser.add_argument(
    "-rs",
    "--random_seed",
    "--random-seed",
    required=False,
    type=int,
    default=1,
    help="Random seed to control color generation.",
)

server_parser = argparse.ArgumentParser(add_help=False)
server_parser.add_argument(
    "-H", "--host", required=False, metavar="HOST", type=str, default="127.0.0.1", help="Dash application host."
)
server_parser.add_argument(
    "-P", "--port", required=False, metavar="PORT", type=int, default=5000, help="Dash application port."
)


def make_server(args=sys.argv[1:]):
    server_praser = argparse.ArgumentParser(parents=[py2file_parser, server_parser], add_help=True)
    parsed_args: argparse.Namespace = server_praser.parse_args(args)
    args_dict = vars(parsed_args)
    graph = get_graph(**args_dict)
    processed_graph = preprocess(graph, **args_dict)
    if args_dict["type"] == "graph":
        plot = graph_plot.get_plot(processed_graph, **args_dict)
        plotly_fig = graphviz_to_plotly(plot)
    elif args_dict["type"] == "chord":
        plotly_fig = chord_plot.get_plot(processed_graph, **args_dict)
    else:
        raise argparse.ArgumentError("Invalid value for argument `type`")
    app = create_app(plotly_fig)
    reloader = hupper.start_reloader("dff.utils.viewer.cli.make_server")
    root_dir = parsed_args.project_root_dir or parsed_args.entry_point.parent
    reloader.watch_files([str(i) for i in root_dir.absolute().glob("./**/*.py")])
    app.run(host=parsed_args.host, port=parsed_args.port, debug=True, dev_tools_hot_reload=True)


def make_image(args=sys.argv[1:]):
    image_parser = argparse.ArgumentParser(parents=[py2file_parser], add_help=True)
    image_parser.add_argument(
        "-f",
        "--format",
        metavar="FORMAT",
        help="Plot output format",
        default="png",
        choices=["png", "jpeg", "pdf", "svg", "gif", "bmp", "dot"],
        type=str,
    )
    image_parser.add_argument(
        "-o",
        "--output_file",
        "--output-file",
        metavar="OUTPUT_FILE",
        help="Image file",
        type=str,
    )
    parsed_args: argparse.Namespace = image_parser.parse_args(args)
    args_dict = vars(parsed_args)
    graph = get_graph(**args_dict)
    processed_graph = preprocess(graph, **args_dict)
    if args_dict["type"] == "graph":
        plot = graph_plot.get_plot(processed_graph, **args_dict)
        image.graphviz_image(plot, parsed_args.output_file, format=parsed_args.format)
    elif args_dict["type"] == "chord":
        plot = chord_plot.get_plot(processed_graph, **args_dict)
        image.plotly_image(plot, parsed_args.output_file, format=parsed_args.format)
    else:
        raise argparse.ArgumentError("Invalid value for argument `type`")
