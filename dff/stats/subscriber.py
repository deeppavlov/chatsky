"""
Subscriber
------------
The following module defines an interface for classes that
subscribe to changes in an extractor pool (:py:class:`~dff.stats.pool.ExtractorPool`).
"""
from abc import ABC, abstractmethod
from .record import StatsRecord


class PoolSubscriber(ABC):
    @abstractmethod
    def on_record_event(self, record: StatsRecord):
        raise NotImplementedError
