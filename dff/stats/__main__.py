"""
Main
----
This module includes command line scripts for Superset dashboard configuration,
e.g. for creating and importing configuration archives.
In a configuration archive, you can override the default settings for db connection, passwords, etc.
with your own parameters that can be passed either as a config file
or as command line arguments.

Examples
********

.. code:: bash

    # Create an importable dashboard config from a yaml-formatted file.
    dff.stats cfg_from_file file.yaml --outfile=/tmp/superset_dashboard.zip

.. code:: bash

    # Create an importable dashboard config from command line arguments.
    dff.stats cfg_from_opts \\
        --db.type=postgresql \\
        --db.user=root \\
        --db.host=localhost \\
        --db.port=5432 \\
        --db.name=test \\
        --db.table=dff_stats \\
        --outfile=/tmp/superset_dashboard.zip

.. code:: bash

    # Import the dashboard file into a running Superset server.
    dff.stats import_dashboard \\
        -U admin \\
        -P admin \\
        -i /tmp/superset_dashboard.zip \\
        -dP password

"""
import sys
import argparse
from typing import Optional

from .cli import import_dashboard, make_zip_config


def main(parsed_args: Optional[argparse.Namespace] = None):
    """
    Function that evokes procedures defined in `cli` module.

    :param parsed_args: Set of command line arguments. If passed, overrides the command line contents.
        See the module docs for reference.
    """
    parser = argparse.ArgumentParser(
        usage="""One of the following subcommands is required:
        dff.stats cfg_from_opts ...
        dff.stats cfg_from_file ...
        dff.stats import_dashboard ...

        Use the `--help` flag to get more information."""
    )
    subparsers = parser.add_subparsers(
        dest="cmd",
        description="""
        'cfg_from_file' & 'cfg_from_opts' commands create a configuration archive;
        'import_dashboard' command uploads the config archive to the Superset server.
        Use any subcommand with the '-h' flag to get more information.
        """,
        required=True,
    )
    opts_parser = subparsers.add_parser(
        "cfg_from_opts",
        usage="""# Create an importable dashboard config from cli arguments.
        dff.stats cfg_from_opts \\
            --db.type=postgresql \\
            --db.user=root \\
            --db.host=localhost \\
            --db.port=5432 \\
            --db.name=test \\
            --db.table=dff_stats \\
            --outfile=/tmp/superset_dashboard.zip
        """,
        help="Create a configuration archive from cli arguments.",
    )
    opts_parser.add_argument(
        "-dT",
        "--db.type",
        choices=["clickhousedb+connect"],
        required=True,
        help="DBMS connection type: 'clickhouse+connect' or ....",
    )
    opts_parser.add_argument("-dU", "--db.user", required=True, help="Database user.")
    opts_parser.add_argument("-dh", "--db.host", required=True, help="Database host.")
    opts_parser.add_argument("-dp", "--db.port", required=True, help="Database port.")
    opts_parser.add_argument("-dn", "--db.name", required=True, help="Name of the database.")
    opts_parser.add_argument("-dt", "--db.table", required=True, help="Name of the table.")
    opts_parser.add_argument("-o", "--outfile", required=True, help="Name for the configuration zip file.")
    file_parser = subparsers.add_parser(
        "cfg_from_file",
        usage="""# Create an importable dashboard config from a yaml file.
        dff.stats cfg_from_file file.yaml --outfile=/tmp/superset_dashboard.zip
        """,
        help="Create a configuration archive from a yaml file.",
    )
    file_parser.add_argument("file", type=str)
    file_parser.add_argument("-o", "--outfile", required=True, help="Name for the configuration zip file.")
    import_parser = subparsers.add_parser(
        "import_dashboard",
        usage="""# Import the dashboard file into a running Superset server.
        dff.stats import_dashboard \\
            -U admin \\
            -P admin \\
            -i /tmp/superset_dashboard.zip \\
            -dP password
        """,
        help="Upload a configuration archive to the Superset server.",
    )
    import_parser.add_argument("-H", "--host", default="localhost", help="Superset host")
    import_parser.add_argument("-p", "--port", default="8088", help="Superset port.")
    import_parser.add_argument("-U", "--username", required=True, help="Superset user.")
    import_parser.add_argument("-P", "--password", required=True, help="Superset password.")
    import_parser.add_argument("-dP", "--db.password", required=True, help="Database password.")
    import_parser.add_argument("-i", "--infile", required=True, help="Zip archive holding configuration files.")

    if parsed_args is None:
        parsed_args = parser.parse_args(sys.argv[1:])

    if not hasattr(parsed_args, "outfile"):  # get outfile
        import_dashboard(parsed_args)
        return

    make_zip_config(parsed_args)


if __name__ == "__main__":
    main()
