"""
Subscriber
----------
The following module defines an interface for classes that
subscribe to changes in an extractor pool (:py:class:`.dff.stats.pool.StatsExtractorPool`).
"""
from abc import ABC, abstractmethod
from dff.script.core.context import Context
from dff.pipeline import ExtraHandlerRuntimeInfo


class PoolSubscriber(ABC):
    """
    :py:class:`.PoolSubscriber` is a base class for pool
    subscriber objects that execute callback functions on new data
    being added to :py:class:`~dff.stats.pool.StatsExtractorPool`.
    """

    @abstractmethod
    async def on_record_event(self, ctx: Context, info: ExtraHandlerRuntimeInfo, data: dict):
        """
        Callback function to execute on new record being appended.

        :param ctx: Request context.
        :param info: Handler runtime info.
        :param data: Target record data.
        """
        raise NotImplementedError
