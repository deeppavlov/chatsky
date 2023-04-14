"""
Pool
----------
This module defines the :py:class:`~ExtractorPool` class.

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
    New extractors can be added with the help of the :py:meth:`new_extractor` decorator.
    These can be accessed by their name:

    .. code-block::

        pool[extractor.__name__]

    After execution, the result of each extractor will be propagated to subscribers.
    Subscribers should be of type :py:class:`~.PoolSubscriber`.

    When you pass a subscriber instance to the :py:meth:`add_subscriber` method,
    you subscribe it to changes in the given pool.

    :param extractors: You can optionally pass a list of extractors to the class constructor or register
        them later.

    """

    def __init__(self, extractors: Optional[List[Callable]] = None):

        self.subscribers: List[PoolSubscriber] = []
        if extractors is not None:
            if not all(callable(i) for i in extractors):
                raise RuntimeError("Non-callable item found in `extractors`")
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

    def add_subscriber(self, subscriber: PoolSubscriber):
        """
        Subscribe a `PoolSubscriber` object to events from this pool.

        :param subscriber: Target subscriber.
        """
        self.subscribers.append(subscriber)

    def new_extractor(self, extractor: Callable) -> Callable:
        """
        This method is used to decorate functions that must be added
        as new extractors.

        :param extractor: Decorated extractor function.
        """
        wrapped_extractor = self._wrap_extractor(extractor)
        self.extractors[extractor.__name__] = wrapped_extractor
        return self.extractors[extractor.__name__]

    def __getitem__(self, key: str):
        return self.extractors.__getitem__(key)
