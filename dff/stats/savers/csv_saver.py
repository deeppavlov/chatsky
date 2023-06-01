"""
CSV Saver
---------
Provides the CSV version of the :py:class:`~dff.stats.savers.saver.Saver`.
The class should be constructed by calling the :py:func:`~dff.stats.savers.saver_factory`
factory with specific parameters.

Statistical data collected to csv cannot be directly displayed in Superset.
Use this class, if you want to permute or analyze your data manually.

"""
import json
import csv
from typing import List, Tuple
import pathlib
import os

from .saver import Saver
from ..record import TraceRecord, LogRecord

TRACE_FIELDNAMES = list(TraceRecord.schema()["properties"].keys())
LOG_FIELDNAMES = list(LogRecord.schema()["properties"].keys())


class CsvSaver(Saver):
    """
    Saves and reads the stats dataframe from a csv file.
    The class should be constructed by calling the :py:func:`~dff.stats.savers.saver_factory`
    factory with specific parameters.

    Statistical data collected to csv cannot be directly displayed in Superset.
    Use this class, if you want to permute or analyze your data manually.

    :param path: The construction path.
        The part after :// should contain a path to the file that pandas will be able to recognize.

        .. code-block::

            CsvSaver("csv://foo/bar.csv")

    :param table: Does not affect the class. Added for constructor uniformity.
    """

    def __init__(self, path: str, _: str = "dff_stats") -> None:
        path = path.partition("://")[2].rstrip(".csv")
        self.log_path = pathlib.Path(path + ".log.csv")
        self.trace_path = pathlib.Path(path + ".trace.csv")

    async def save(self, data: List[Tuple[TraceRecord, LogRecord]]) -> None:
        if len(data) == 0:
            return

        saved_data = []
        if all(map(lambda x: x.exists() and os.path.getsize(x) > 0, [self.log_path, self.trace_path])):
            saved_data = await self.load()

        data = saved_data + data

        log_file = open(self.log_path, "w", encoding="utf-8")
        trace_file = open(self.trace_path, "w", encoding="utf-8")
        log_writer = csv.DictWriter(
            log_file, fieldnames=LOG_FIELDNAMES, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC
        )
        trace_writer = csv.DictWriter(
            trace_file, fieldnames=TRACE_FIELDNAMES, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC
        )
        log_writer.writeheader()
        trace_writer.writeheader()
        for item in data:
            trace_writer.writerow(item[0].dict())
            log_writer.writerow({**item[1].dict(), "Body": json.dumps(item[1].Body, default=str)})
        log_file.close()
        trace_file.close()

    async def load(self) -> List[Tuple[TraceRecord, LogRecord]]:
        log_file = open(self.log_path, "r", encoding="utf-8")
        trace_file = open(self.trace_path, "r", encoding="utf-8")
        log_reader = csv.DictReader(log_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        trace_reader = csv.DictReader(trace_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        items = []
        for trace, log in zip(trace_reader, log_reader):
            log["Body"] = json.loads(log["Body"])
            items.append((TraceRecord.parse_raw(json.dumps(trace)), LogRecord.parse_raw(json.dumps(log))))
        log_file.close()
        trace_file.close()
        return items

    async def create_table(self) -> None:
        return None
