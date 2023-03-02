import os
from argparse import Namespace
import pytest

from dff.stats.__main__ import main
from tests.db_list import SUPERSET_ACTIVE


@pytest.mark.parametrize(
    ["args"],
    [
        (
            Namespace(
                **{
                    "outfile": "1.zip",
                    "db.type": "postgresql",
                    "db.user": "root",
                    "db.host": "localhost",
                    "db.port": "5000",
                    "db.name": "test",
                    "db.table": "dff_stats",
                }
            ),
        ),
        (
            Namespace(
                **{
                    "outfile": "2.zip",
                    "db.type": "mysql+mysqldb",
                    "db.user": "root",
                    "db.host": "localhost",
                    "db.port": "5000",
                    "db.name": "test",
                    "db.table": "dff_stats",
                }
            ),
        ),
        (
            Namespace(
                **{
                    "outfile": "3.zip",
                    "db.type": "clickhousedb+connect",
                    "db.user": "root",
                    "db.host": "localhost",
                    "db.port": "5000",
                    "db.name": "test",
                    "db.table": "dff_stats",
                }
            ),
        ),
    ],
)
def test_main(testing_cfg_dir, args):
    args.outfile = testing_cfg_dir + args.outfile
    main(args)
    assert os.path.exists(args.outfile)
    assert os.path.isfile(args.outfile)
    assert os.path.getsize(args.outfile) > 2200


@pytest.mark.skipif(not SUPERSET_ACTIVE, reason="Superset server not active")
@pytest.mark.parametrize(
    ["zip_args", "upload_args"],
    [
        (
            Namespace(
                **{
                    "outfile": "1.zip",
                    "db.type": "postgresql",
                    "db.user": "root",
                    "db.host": "localhost",
                    "db.port": "5000",
                    "db.name": "test",
                    "db.table": "dff_stats",
                }
            ),
            Namespace(
                **{
                    "username": os.getenv("SUPERSET_USERNAME"),
                    "password": os.getenv("SUPERSET_PASSWORD"),
                    "db.password": "qwerty",
                    "infile": "1.zip",
                }
            ),
        ),
    ],
)
def test_upload(testing_cfg_dir, zip_args, upload_args):
    zip_args.outfile = testing_cfg_dir + zip_args.outfile
    # main(zip_args)
    upload_args.infile = testing_cfg_dir + upload_args.infile
    # main(upload_args)


@pytest.mark.parametrize(["cmd"], [("dff.stats -h",), ("dff.stats --help",)])
def test_help(cmd):
    res = os.system(cmd)
    assert res == 0
