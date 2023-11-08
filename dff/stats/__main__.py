"""
Main
----
This module includes command line scripts for Superset dashboard configuration,
e.g. for creating and importing configuration archives.
In a configuration archive, you can define such settings as passwords, networking addressses etc.
using your own parameters that can be passed as a config file and overridden by command line arguments.

Examples
********

.. code:: bash

        # Create and import a configuration archive.
        # The import overrides existing dashboard configurations.
        dff.stats config.yaml \\
            -U superset_user \\
            -P superset_password \\
            -dP database_password \\
            --db.user=database_user \\
            --db.host=clickhouse \\
            --db.port=8123 \\
            --db.name=test \\
            --db.table=otel_logs \\
            --outfile=config_artifact.zip

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
        The import overrides existing dashboard configurations if present.
        The function accepts a yaml file; also, all of the options can also be overridden
        via the command line. Setting passwords interactively is supported.

        dff.stats config.yaml \\
            -U superset_user \\
            -P superset_password \\
            -dP database_password \\
            --db.user=database_user \\
            --db.host=clickhouse \\
            --db.port=8123 \\
            --db.name=test \\
            --db.table=otel_logs \\
            --outfile=config_artifact.zip

        Use the `--help` flag to get more information."""
    )
    parser.add_argument("file", type=str)
    parser.add_argument(
        "-dD",
        "--db.driver",
        choices=["clickhousedb+connect"],
        help="DBMS driver.",
        default="clickhousedb+connect",
    )
    parser.add_argument("-dU", "--db.user", help="Database user.")
    parser.add_argument("-dh", "--db.host", default="clickhouse", help="Database host.")
    parser.add_argument("-dp", "--db.port", help="Database port.")
    parser.add_argument("-dn", "--db.name", help="Name of the database.")
    parser.add_argument("-dt", "--db.table", default="otel_logs", help="Name of the table.")
    parser.add_argument("-o", "--outfile", help="Optionally persist the configuration as a zip file.")
    parser.add_argument("-i", "--infile", help="Configuration zip file to import.")
    parser.add_argument("-H", "--host", default="localhost", help="Superset host")
    parser.add_argument("-p", "--port", default="8088", help="Superset port.")
    parser.add_argument("-U", "--username", required=True, help="Superset user.")
    parser.add_argument(
        "-P",
        "--password",
        dest="password",
        type=str,
        action=PasswordAction,
        help="Superset password.",
        nargs="?",
        required=True,
    )
    parser.add_argument(
        "-dP",
        "--db.password",
        dest="db.password",
        type=str,
        action=PasswordAction,
        help="Database password.",
        required=True,
        nargs="?",
    )

    if parsed_args is None:
        parsed_args = parser.parse_args(sys.argv[1:])

    file = None
    use_infile = hasattr(parsed_args, "infile") and parsed_args.infile is not None
    use_outfile = hasattr(parsed_args, "outfile") and parsed_args.outfile is not None
    if not use_infile:
        file = make_zip_config(parsed_args)
    else:
        file = parsed_args.infile

    import_dashboard(parsed_args, zip_file=str(file))

    if not use_infile and not use_outfile:
        file.unlink()


if __name__ == "__main__":
    main()
