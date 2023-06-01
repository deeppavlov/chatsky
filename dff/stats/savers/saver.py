"""
Base Saver
----------
Provides the base class :py:class:`~dff.stats.savers.saver.Saver`.
It serves as an interface class
that defines methods for saving and loading data.

"""
from typing import List, Tuple
from abc import ABC, abstractmethod

from ..record import LogRecord, TraceRecord


class Saver(ABC):
    """
    This interface requires two methods to be implemented:

    #. :py:meth:`~dff.stats.savers.saver.Saver.save`
    #. :py:meth:`~dff.stats.savers.saver.Saver.load`

    You can construct your own `Saver` by subclassing the abstract interface and implementing
    the methods named above.
    """

    @abstractmethod
    async def save(
        self,
        data: List[Tuple[TraceRecord, LogRecord]],
    ) -> None:
        """
        Save the data to a database or a file.
        Append if the table already exists.

        :param data: Collection of data to persist to the database.
        """
        raise NotImplementedError

    @abstractmethod
    async def load(self) -> List[Tuple[TraceRecord, LogRecord]]:
        """
        Load the data from a database or a file.

        """
        raise NotImplementedError

    @abstractmethod
    async def create_table(self) -> None:
        """
        Create the target table in the DBM system.

        """
        raise NotImplementedError
