from pathlib import Path
from typing import Optional
import argparse

import hupper

from .graph import get_graph
from .plot import get_plot
from .app import create_app
from .image import image


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
py2file_parser.add_argument("-r", "--show_response", action="store_true", help="Show node response values.")
py2file_parser.add_argument("-m", "--show_misc", action="store_true", help="Show node misc values.")
py2file_parser.add_argument("-l", "--show_local", action="store_true", help="Show local transitions.")
py2file_parser.add_argument("-p", "--show_processing", action="store_true", help="Show processing functions.")
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
    "-P", "--port", required=False, metavar="PORT", type=int, default=5000, help="Dash application port."
)


def run_server(
    entry_point,
    project_root_dir,
    show_response,
    show_processing,
    show_misc,
    show_global,
    show_local,
    show_isolates,
    random_seed,
    host,
    port,
):
    graph = get_graph(entry_point, project_root_dir)
    plot = get_plot(
        graph, show_response, show_processing, show_misc, show_global, show_local, show_isolates, random_seed
    )
    app = create_app(plot)
    app.run(host=host, port=port, debug=True, dev_tools_hot_reload=True)


def make_server():
    server_praser = argparse.ArgumentParser(parents=[py2file_parser, server_parser], add_help=True)
    args: argparse.Namespace = server_praser.parse_args()
    reloader = hupper.start_reloader(
        "dff.utils.viewer.cli.run_server",
        worker_kwargs=dict(
            entry_point=args.entry_point,
            project_root_dir=args.project_root_dir,
            show_response=args.show_response,
            show_processing=args.show_processing,
            show_misc=args.show_misc,
            show_global=args.show_global,
            show_local=args.show_local,
            show_isolates=args.show_isolates,
            random_seed=args.random_seed,
            host=args.host,
            port=args.port,
        ),
    )
    reloader.logger.warn("1!")
    reloader.watch_files([str(i) for i in args.project_root_dir.absolute().glob("./**/*.py")])
    reloader.logger.warn("2!")
    reloader.logger.warn([str(i) for i in args.project_root_dir.absolute().glob("./**/*.py")])
    run_server()


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
    image(plot, args.output_file, format=args.format)
