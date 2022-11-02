"""
Main
*********
This module is a script designed to adapt the standard Superset dashboard to 
user-specific settings. Settings can be passed to the script with a config file
or as command line arguments.

Examples
**********

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
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd", description="update or import config", required=True)
    opts_parser = subparsers.add_parser("cfg_from_opts")
    opts_parser.add_argument("-dT", "--db.type", choices=["postgresql", "clickhousedb+connect"], required=True)
    opts_parser.add_argument("-dU", "--db.user", required=True)
    opts_parser.add_argument("-dh", "--db.host", required=True)
    opts_parser.add_argument("-dp", "--db.port", required=True)
    opts_parser.add_argument("-dn", "--db.name", required=True)
    opts_parser.add_argument("-dt", "--db.table", required=True)
    opts_parser.add_argument("-o", "--outfile", required=True)
    file_parser = subparsers.add_parser("cfg_from_file")
    file_parser.add_argument("file", type=str)
    file_parser.add_argument("-o", "--outfile", required=True)
    import_parser = subparsers.add_parser("import_dashboard")
    import_parser.add_argument("-U", "--username", required=True)
    import_parser.add_argument("-P", "--password", required=True)
    import_parser.add_argument("-dP", "--db.password", required=True)
    import_parser.add_argument("-i", "--infile", required=True)

    if parsed_args is None:
        parsed_args = parser.parse_args(sys.argv[1:])

    if not hasattr(parsed_args, "outfile"):  # get outfile
        import_dashboard(parsed_args)
        return

    make_zip_config(parsed_args)


if __name__ == "__main__":
    main()
