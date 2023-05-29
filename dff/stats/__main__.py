"""
Main
----
This module is a script designed to adapt the standard Superset dashboard to
user-specific settings. Settings can be passed to the script with a config file
or as command line arguments.

Examples
********

.. code:: bash

    dff.stats cfg_from_file file.yaml --outfile=/tmp/superset_dashboard.zip

.. code:: bash

    dff.stats cfg_from_opts \\
        --db.type=postgresql \\
        --db.user=root \\
        --db.host=localhost \\
        --db.port=5432 \\
        --db.name=test \\
        --db.table=dff_stats \\
        --outfile=/tmp/superset_dashboard.zip

.. code:: bash

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
    parser = argparse.ArgumentParser(description="Update or import config for Superset dashboard.")
    subparsers = parser.add_subparsers(
        dest="cmd",
        description="'cfg_from*' commands create a config archive; 'import_dashboard' command imports a config archive",
        required=True,
    )
    opts_parser = subparsers.add_parser("cfg_from_opts", help="Create a configuration archive from cli arguments.")
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
    file_parser = subparsers.add_parser("cfg_from_file", help="Create a configuration archive from a yaml file.")
    file_parser.add_argument("file", type=str)
    file_parser.add_argument("-o", "--outfile", required=True, help="Name for the configuration zip file.")
    import_parser = subparsers.add_parser("import_dashboard", help="Upload a configuration archive to Superset.")
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
