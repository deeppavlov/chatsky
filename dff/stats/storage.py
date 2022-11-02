"""
StatsStorage
*************
| Defines the StatsStorage class that can be used to persist information to a database.

"""

import asyncio
from typing import List

from .savers import Saver, make_saver
from .pool import ExtractorPool
from .record import StatsRecord
from .subscriber import PoolSubscriber


class StatsStorage(PoolSubscriber):
    """
    This class serves as an intermediate collection of data records that stores
    batches of data and persists them to a database. The batch size is individual
    for each instance.

    Parameters
    ----------

    saver: :py:class:`~dff.stats.savers.Saver`
        An instance of the Saver class that is used to save the collected data.
    batch_size: int = 1
        The number of records that should be accumulated before they get persisted to the db.

    """

    def __init__(self, saver: Saver, batch_size: int = 1) -> None:
        self.saver: Saver = saver
        self.batch_size: int = batch_size
        self.data: List[StatsRecord] = []

    async def save(self):
        if len(self.data) >= self.batch_size:
            await self.flush()

    async def flush(self):
        async with asyncio.Lock():
            await self.saver.save(self.data) # TODO: "None" is not awaitable
        self.data.clear()

    async def on_record_event(self, record: StatsRecord):
        self.data.append(record)
        await self.save()

    def add_extractor_pool(self, pool: ExtractorPool):
        pool.subscribers.append(self)

    @classmethod
    def from_uri(cls, uri: str, table: str = "df_stats", batch_size: int = 1):
        """
        Instantiates the saver from the given arguments.
        """
        return cls(saver=make_saver(uri, table), batch_size=batch_size)
