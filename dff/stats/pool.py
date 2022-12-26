"""
Pool
----------
This module includes the :py:class:`~ExtractorPool` class.

"""
import functools
import asyncio
from typing import List, Callable, Optional

from dff.script import Context
from dff.pipeline import ExtraHandlerRuntimeInfo
from .subscriber import PoolSubscriber


class ExtractorPool:
    """
    This class can be used to store sets of wrappers for statistics collection a.k.a. extractors.
    New wrappers can be added with the :py:meth:`new_extractor` decorator.
    The added wrappers can be accessed by their name:

    .. code: python

        pool[extractor.__name__]

    After execution, the result of each wrapper will be propagated to subscribers.
    Subscribers can belong to any class, given that they implement the `on_record_event` method.
    Currently, this method exists in the :py:class:`StatsStorage` class.

    When you call the :py:meth:`add_extractor_pool` method on the :py:class:`~StatsStorage`, you subscribe it
    to changes in the given pool.

    :param extractors: You can pass a set of wrappers as a list on the class construction.
        They will be registered as normal.

    """

    def __init__(self, extractors: Optional[List[Callable]] = None):

        self.subscribers: List[PoolSubscriber] = []
        if extractors is not None:
            assert all(isinstance(i, Callable) for i in extractors), "Non-callable item found in `extractors`"
            self.extractors = {item.__name__: self._wrap_extractor(item) for item in extractors}
        else:
            self.extractors = {}

    def _wrap_extractor(self, extractor: Callable) -> Callable:
        @functools.wraps(extractor)
        async def extractor_wrapper(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
            if asyncio.iscoroutinefunction(extractor):
                result = await extractor(ctx, _, info)
            else:
                result = extractor(ctx, _, info)

            if result is None:
                return result

            for subscriber in self.subscribers:
                await subscriber.on_record_event(result)
            return result

        return extractor_wrapper

    def new_extractor(self, extractor: Callable) -> Callable:
        wrapped_extractor = self._wrap_extractor(extractor)
        self.extractors[extractor.__name__] = wrapped_extractor
        return self.extractors[extractor.__name__]

    def __getitem__(self, key: str):
        return self.extractors.__getitem__(key)
