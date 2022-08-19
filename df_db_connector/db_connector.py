"""
db_connector
---------------------------
| Base module. Provided classes:
| Abstract connector interface :py:class:`~df_db_connector.db_connector.DBAbstractConnector`.
| An intermediate class to inherit from: :py:class:`~df_db_connector.db_connector.DBConnector`

"""
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable


class DBAbstractConnector(ABC):
    """
    | An abstract interface for DF DB connectors. It includes the most essential methods of the python `dict` class.
    | Can not be instantiated.
    """

    def __init__(self) -> None:
        pass

    @abstractmethod
    def __getitem__(self, key: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def __setitem__(self, key: str, value: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def __delitem__(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def __len__(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def get(self, item) -> Any:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError


class DBConnector(DBAbstractConnector):
    """
    An intermediate class between the abstract connector interface,
    :py:class:`~df_db_connector.db_connector.DBAbstractConnector`, and concrete implementations.

    Parameters
    ----------
    path: str
        | Parameter `path` should be set with the URI of the database.
        | It includes a prefix and the required connection credentials.
        | Example: postgresql://user:password@host:port/database
        | In the case of classes that save data to hard drive instead of external databases
        | you need to specify the location of the file, like you do in sqlite.
        | Keep in mind that in Windows you will have to use double backslashes '\\'
        | instead of forward slashes '/' when defining the file path.

    """

    def __init__(self, path: str):
        prefix, _, file_path = path.partition("://")
        self.full_path = path
        self.path = file_path
        self._lock = threading.Lock()

    def get(self, key: str, default=None) -> Any:
        try:
            value = self.__getitem__(key)
        except KeyError:
            value = default
        return value


def threadsafe_method(func: Callable):
    """
    A decorator that makes sure methods of an object instance are threadsafe.
    """

    def _synchronized(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)

    return _synchronized
