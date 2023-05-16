"""
Pool
----
This module defines the :py:class:`.StatsExtractorPool` class.

"""
import functools
import asyncio
from typing import List, Callable

from pydantic import validate_arguments
from pydantic.typing import Literal
from dff.script import Context
from dff.pipeline import ExtraHandlerRuntimeInfo, ExtraHandlerType, ExtraHandlerFunction
from .subscriber import PoolSubscriber


class StatsExtractorPool:
    """
    This class can be used to store sets of wrappers for statistics collection a.k.a. extractors.
    New extractors can be added with the help of the :py:meth:`add_extractor` method.
    These can be accessed by their name and handler_type:

    .. code-block::

        pool[handler_type][extractor.__name__]

    After execution, the result of each extractor will be propagated to subscribers.
    Subscribers should be of type :py:class:`~.PoolSubscriber`.

    When you pass a subscriber instance to the :py:meth:`add_subscriber` method,
    you subscribe it to changes in the given pool.

    :param extractors: You can optionally pass a list of extractors to the class constructor or register
        them later.

    """

    def __init__(self):
        self.subscribers: List[PoolSubscriber] = []
        self.extractors = {ExtraHandlerType.BEFORE: {}, ExtraHandlerType.AFTER: {}}

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

    @validate_arguments
    def __getitem__(self, key: ExtraHandlerType):
        return self.extractors[key]

    def add_subscriber(self, subscriber: PoolSubscriber):
        """
        Subscribe a `PoolSubscriber` object to events from this pool.

        :param subscriber: Target subscriber.
        """
        self.subscribers.append(subscriber)

    @validate_arguments
    def add_extractor(
        self,
        extractor: Callable,
        handler_type: Literal[ExtraHandlerType.BEFORE, ExtraHandlerType.AFTER] = ExtraHandlerType.AFTER,
    ) -> ExtraHandlerFunction:
        """Generic function for adding extractors.
        Requires handler type, e.g. 'before' or 'after'.

        :param extractor: Decorated extractor function.
        :param handler_type: Function execution stage: `before` or `after`.
        """
        wrapped_extractor = self._wrap_extractor(extractor)
        self.extractors[handler_type][extractor.__name__] = wrapped_extractor
        return self.extractors[handler_type][extractor.__name__]

    def add_before_extractor(self, extractor: Callable) -> ExtraHandlerFunction:
        """
        This method functions as a decorator and adds the decorated function
        to the `before` group.

        :param extractor: Decorated extractor function.
        """
        return self.add_extractor(extractor, ExtraHandlerType.BEFORE)

    def add_after_extractor(self, extractor: Callable) -> ExtraHandlerFunction:
        """
        This method functions as a decorator and adds the decorated function
        to the `after` group.

        :param extractor: Decorated extractor function.
        """
        return self.add_extractor(extractor, ExtraHandlerType.AFTER)

    @property
    def before_handlers(self) -> List[ExtraHandlerFunction]:
        return list(self.extractors[ExtraHandlerType.BEFORE].values())

    @property
    def after_handlers(self) -> List[ExtraHandlerFunction]:
        return list(self.extractors[ExtraHandlerType.AFTER].values())
