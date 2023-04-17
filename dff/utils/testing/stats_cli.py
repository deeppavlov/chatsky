"""
The `stats_cli` module provides a command-line interface
to parse configuration settings for a database connection.
It uses the argparse module for parsing command-line arguments,
and the OmegaConf module for parsing configuration files in YAML format.
"""
import argparse
import sys

from omegaconf import OmegaConf

common_opts = argparse.ArgumentParser(add_help=False)
common_opts.add_argument("-dP", "--db.password", required=True)

parser = argparse.ArgumentParser(
    usage="To run this example, provide the database credentials, using one of the commands below."
)
subparsers = parser.add_subparsers(dest="cmd", description="Configuration source", required=True)
opts_parser = subparsers.add_parser("cfg_from_opts", parents=[common_opts])
opts_parser.add_argument("-dT", "--db.type", choices=["postgresql", "clickhouse"], required=True)
opts_parser.add_argument("-dU", "--db.user", required=True)
opts_parser.add_argument("-dh", "--db.host", required=True)
opts_parser.add_argument("-dp", "--db.port", required=True)
opts_parser.add_argument("-dn", "--db.name", required=True)
opts_parser.add_argument("-dt", "--db.table", required=True)
file_parser = subparsers.add_parser("cfg_from_file", parents=[common_opts])
file_parser.add_argument("file", type=str)
uri_parser = subparsers.add_parser("cfg_from_uri")
uri_parser.add_argument(
    "--uri", required=True, help="Enter the uri in the following format: `dbms://user:password@host:port/db`"
)
uri_parser.add_argument("-dt", "--db.table", help="Optionally, set table name.")


def parse_args():
    """
    Parses command-line arguments and returns a dictionary
    containing the database connection settings.
    The function determines the configuration source
    based on the command-line arguments provided.

    The parser object provides two sub-commands,
    cfg_from_opts and cfg_from_file, and a third sub-command, cfg_from_uri,
    which is used to specify a database connection string
    in the command-line arguments.
    """
    parsed_args = parser.parse_args(sys.argv[1:])

    if hasattr(parsed_args, "uri"):
        table = vars(parsed_args).get("db.table")
        return {"uri": parsed_args.uri, "table": table}

    elif hasattr(parsed_args, "file"):  # parse yaml input
        conf = OmegaConf.load(parsed_args.file)
        sys.argv = [__file__] + [f"{key.lstrip('-')}={value}" for key, value in parsed_args.__dict__.items()]
        conf.merge_with_cli()

    else:
        sys.argv = [__file__] + [f"{key}={value}" for key, value in parsed_args.__dict__.items()]
        conf = OmegaConf.from_cli()

    return {
        "uri": "{type}://{user}:{password}@{host}:{port}/{name}".format(**conf._content["db"]),
        "table": conf._content["db"]["table"],
    }
