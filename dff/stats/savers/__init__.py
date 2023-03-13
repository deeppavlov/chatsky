from .clickhouse import ClickHouseSaver
from .postgresql import PostgresSaver
from .csv_saver import CsvSaver
from .saver import Saver

SAVER_MAPPING = {"csv": CsvSaver, "postgresql": PostgresSaver, "clickhouse": ClickHouseSaver}


def make_saver(path: str, table: str = "dfd_stats") -> Saver:
    db_type, _, credentials = path.partition("://")
    assert all((db_type, credentials))
    return SAVER_MAPPING[db_type](path, table)
