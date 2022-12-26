"""
Saver
------------
Provides the base class :py:class:`~dff.stats.savers.saver.Saver`.
It serves as an interface class
that defines methods for saving and loading data.

"""
from typing import List
from abc import ABC, abstractmethod

from ..record import StatsRecord


class Saver(ABC):
    """
    :py:class:`~dff.stats.savers.saver.Saver` interface requires two methods to be impemented:

    #. :py:meth:`~dff.stats.savers.saver.Saver.save`
    #. :py:meth:`~dff.stats.savers.saver.Saver.load`

    You can construct your own `Saver` by subclassing the abstract interface and implementing
    the methods named above.

    :param path: A string that contains a prefix and a url of the target data storage, separated by ://.
    :param table: Sets the name of the db table to use, if necessary. Defaults to "dff_stats".
    """

    @abstractmethod
    def save(
        self,
        data: List[StatsRecord],
    ) -> None:
        """
        Save the data to a database or a file.
        Append if the table already exists.

        :param data: Collection of data to persist to the database.
        """
        raise NotImplementedError

    @abstractmethod
    def load(self) -> List[StatsRecord]:
        """
        Load the data from a database or a file.

        """
        raise NotImplementedError
