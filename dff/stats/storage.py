"""
Storage
-------
The following module includes the :py:class:`.StatsStorage` class
that can be used to persist information to a database.

"""

import asyncio
from typing import List, Tuple
from dff.script.core.context import Context
from dff.pipeline import ExtraHandlerRuntimeInfo

from .savers import Saver, saver_factory
from .record import StatsLogRecord, StatsTraceRecord
from .subscriber import PoolSubscriber


class StatsStorage(PoolSubscriber):
    """
    This class serves as an intermediate collection of data records that stores
    batches of data and persists them to a database. The batch size is individual
    for each instance.

    :param saver: An instance of the Saver class that is used to save the collected data.
    :param batch_size: The number of records that triggers the saving operations.

    """

    def __init__(self, saver: Saver, batch_size: int = 1) -> None:
        self.saver: Saver = saver
        self.batch_size: int = batch_size
        self.lock = asyncio.Lock()
        self.data: List[Tuple[StatsTraceRecord, StatsLogRecord]] = []

    async def save(self):
        """
        Calls the :py:meth:`~flush` function when the
        number of records is greater than or equal to `batch_size`.
        """
        if len(self.data) >= self.batch_size:
            await self.flush()

    async def flush(self):
        """
        Persist and discard the collected records.
        """
        await self.saver.save(self.data)
        self.data.clear()

    async def on_record_event(self, ctx: Context, info: ExtraHandlerRuntimeInfo, data: dict):
        """
        Callback that gets executed after a record has been added.

        :param ctx: Request context.
        :param info: Extra handler runtime info.
        :param data: Target data.
        """
        async with self.lock:
            trace_record = StatsTraceRecord.from_context(ctx, info, data)
            log_record = StatsLogRecord.from_context(ctx, info, data)
            log_record.SpanId = trace_record.SpanId
            log_record.TraceId = trace_record.TraceId
            self.data.append((trace_record, log_record))
            await self.save()

    @classmethod
    def from_uri(cls, uri: str, logs_table: str = "otel_logs", traces_table: str = "otel_traces", batch_size: int = 1):
        """
        Instantiates the saver from the given arguments.

        :param uri: Database identifier.
        :param table: Database table to use for data persistence.
        :param batch_size: Number of records that will trigger the saving operation.
        """
        saver = saver_factory(uri, logs_table=logs_table, traces_table=traces_table)
        return cls(saver=saver, batch_size=batch_size)
