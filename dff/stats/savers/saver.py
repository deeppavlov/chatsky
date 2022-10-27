"""
Saver
******
Provides the base class :py:class:`~df_stats.savers.saver.Saver`. 
It is an interface class that defines methods for saving and loading dataframes.
On the other hand, it is also used to automatically construct the child classes 
depending on the input parameters. See the class documentation for more info.

"""
from typing import List, Optional # TODO: Optional is not used
from abc import ABC, abstractmethod

from ..record import StatsRecord


class Saver(ABC):
    """
    :py:class:`~df_stats.savers.saver.Saver` interface requires two methods to be impemented:

    #. :py:meth:`~df_stats.savers.saver.Saver.save`
    #. :py:meth:`~df_stats.savers.saver.Saver.load`

    | A call to Saver is needed to instantiate one of the predefined child classes.
    | The subclass is chosen depending on the `path` parameter value (see Parameters).

    | Your own Saver can be implemented in the following manner:
    | You should subclass the `Saver` class and pass the url prefix as the `storage_type` parameter.
    | Abstract methods `save` and `load` should necessarily be implemented.

    .. code: python
        class MongoSaver(Saver, storage_type="mongo"):
            def __init__(self, path, table):
                ...

            def save(self, data):
                ...

            def load(self):
                ...

    Parameters
    ----------

    path: str
        A string that contains a prefix and a url of the target data storage, separated by ://.
        The prefix is used to automatically import a child class from one of the submodules
        and instantiate it.
        For instance, a call to `Saver("csv://...")` will eventually produce a :py:class:`~df_stats.savers.csv_saver.CsvSaver`,
        while a call to `Saver("clickhouse://...")` produces a :py:class:`~df_stats.savers.clickhouse.ClickHouseSaver`

    table: str
        Sets the name of the db table to use, if necessary. Defaults to "dff_stats".
    """

    @abstractmethod
    def save(
        self,
        data: List[StatsRecord],
    ) -> None:
        """
        Save the data to a database or a file.
        Append if the table already exists.

        Parameters
        ----------

        dfs: List[pd.DataFrame]
        column_types: Optional[Dict[str, str]] = None
        parse_dates: Union[List[str], bool] = False
        """
        raise NotImplementedError

    @abstractmethod
    def load(self) -> List[StatsRecord]:
        """
        Load the data from a database or a file.

        Parameters
        ----------

        column_types: Optional[Dict[str, str]] = None
        parse_dates: Union[List[str], bool] = False
        """
        raise NotImplementedError
