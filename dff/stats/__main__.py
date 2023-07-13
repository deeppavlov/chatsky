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
from .utils import PasswordAction


def main(parsed_args: Optional[argparse.Namespace] = None):
    """
    Function that evokes procedures defined in `cli` module.

    :param parsed_args: Set of command line arguments. If passed, overrides the command line contents.
        See the module docs for reference.
    """
    parser = argparse.ArgumentParser(
        usage="""Creates a configuration archive and uploads it to the Superset server.
        The function accepts a configuration yaml file. All of the options can also be overridden
        via the command line. Setting passwords interactively is supported.

        dff.stats config.yaml \\
            -U superset_user \\
            -P superset_password \\
            -dP password
            --db.type=postgresql \\
            --db.user=root \\
            --db.host=localhost \\
            --db.port=5432 \\
            --db.name=test \\
            --db.table=dff_stats \\
            --outfile=config_artifact.zip

        Use the `--help` flag to get more information."""
    )
    parser.add_argument("file", type=str)
    parser.add_argument(
        "-dT",
        "--db.type",
        choices=["clickhousedb+connect"],
        help="DBMS connection type: 'clickhouse+connect' or ....",
    )
    parser.add_argument("-dU", "--db.user", help="Database user.")
    parser.add_argument("-dh", "--db.host", help="Database host.")
    parser.add_argument("-dp", "--db.port", help="Database port.")
    parser.add_argument("-dn", "--db.name", help="Name of the database.")
    parser.add_argument("-dt", "--db.table", help="Name of the table.")
    parser.add_argument("-o", "--outfile", help="Optionally persist the configuration as a zip file.")
    parser.add_argument("-H", "--host", default="localhost", help="Superset host")
    parser.add_argument("-p", "--port", default="8088", help="Superset port.")
    parser.add_argument("-U", "--username", required=True, help="Superset user.")
    parser.add_argument("-P", "--password", type=str, action=PasswordAction, help="Superset password.", required=True)
    parser.add_argument(
        "-dP", "--db.password", type=str, action=PasswordAction, help="Database password.", required=True
    )

    if parsed_args is None:
        parsed_args = parser.parse_args(sys.argv[1:])

    outfile = make_zip_config(parsed_args)
    import_dashboard(parsed_args, zip_file=str(outfile))

    if not hasattr(parsed_args, "outfile"):
        outfile.unlink()


if __name__ == "__main__":
    main()
