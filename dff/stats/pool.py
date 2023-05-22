"""
Pool
----
This module defines the :py:class:`.StatsExtractorPool` class.

"""
import functools
import asyncio
from typing import List, Callable, Dict

from dff.script import Context
from dff.pipeline import ExtraHandlerRuntimeInfo, ExtraHandlerType, ExtraHandlerFunction
from .subscriber import PoolSubscriber


class StatsExtractorPool:
    """
    This class can be used to store sets of wrappers for statistics collection a.k.a. extractors.
    Extractors are stored inside user-defined groups which allows for easy access to related functions.
    New extractors can be added with the help of the :py:meth:`add_extractor` method,
    specifying a group is required.

    Lists of all extractors inside particular groups are available as attributes of a pool instance.

    .. code-block::

        pool.group

    Individual extractors can also be accessed as dictionary items:

    .. code-block::

        pool[group][extractor.__name__]

    Return values of all extractors get propagated to the subscribers of the pool.
    New subscribers can be added using the :py:meth:`add_subscriber` method.
    Subscribers should mandatorily implement the :py:class:`~.PoolSubscriber` interface.
    """

    def __init__(self):
        self.subscribers: List[PoolSubscriber] = []
        self.extractors: Dict[str, Dict[str, ExtraHandlerFunction]] = {}

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

    def __getitem__(self, key: ExtraHandlerType):
        return self.extractors[key]

    def add_subscriber(self, subscriber: PoolSubscriber):
        """
        Subscribe a `PoolSubscriber` object to events from this pool.

        :param subscriber: Target subscriber.
        """
        self.subscribers.append(subscriber)

    def add_extractor(self, group: str) -> ExtraHandlerFunction:
        def add_extractor_inner(extractor: Callable):
            """Generic function for adding extractors.
            Requires handler type, e.g. 'before' or 'after'.

            :param extractor: Decorated extractor function.
            :param group: Function execution stage: `before` or `after`.
            """
            wrapped_extractor = self._wrap_extractor(extractor)
            self.extractors[group] = {**self.extractors.get(group, {}), extractor.__name__: wrapped_extractor}
            return wrapped_extractor

        return add_extractor_inner

    def __getattr__(self, attr: str):
        if attr not in self.extractors:
            raise AttributeError(f"Attribute {attr} does not exist.")
        return [item for item in self.extractors.get(attr, {}).values()]

    @property
    def all_handlers(self) -> List[ExtraHandlerFunction]:
        return [item for container in self.extractors.values() for item in container.values()]
