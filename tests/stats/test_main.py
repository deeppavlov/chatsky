import pytest
import os
from argparse import Namespace

from dff.stats.__main__ import main


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
