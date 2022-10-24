from abc import ABC, abstractmethod
from .record import StatsRecord


class PoolSubscriber(ABC):
    @abstractmethod
    def on_record_event(self, record: StatsRecord):
        raise NotImplementedError
