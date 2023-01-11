"""
Database
--------
Base module. Provided classes:
    - Abstract context storage interface :py:class:`.DBAbstractContextStorage`.
    - An intermediate class to inherit from: :py:class:`.DBContextStorage`
"""
import importlib
import threading
from functools import wraps
from abc import ABC, abstractmethod
from typing import Any, Callable

from .protocol import PROTOCOLS


class DBAbstractContextStorage(ABC):
    """
    An abstract interface for `dff` DB context storages.
    It includes the most essential methods of the python `dict` class.
    Can not be instantiated.
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


class DBContextStorage(DBAbstractContextStorage):
    """
    An intermediate class between the abstract context storage interface,
    :py:class:`.DBAbstractContextStorage`, and concrete implementations.

    :param path: Parameter `path` should be set with the URI of the database.
        It includes a prefix and the required connection credentials.
        Example: postgresql://user:password@host:port/database
        In the case of classes that save data to hard drive instead of external databases
        you need to specify the location of the file, like you do in sqlite.
        Keep in mind that in Windows you will have to use double backslashes '\\'
        instead of forward slashes '/' when defining the file path.
    :type path: str

    """

    def __init__(self, path: str):
        _, _, file_path = path.partition("://")
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

    @wraps(func)
    def _synchronized(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)

    return _synchronized


def context_storage_factory(path: str, **kwargs):
    """
    Use context_storage_factory to lazy import context storage types and instantiate them.
    The function takes a database connection URI or its equivalent. It should be prefixed with database name,
    followed by the symbol triplet '://'.
    Then, you should list the connection parameters like this: user:password@host:port/database
    The whole URI will then look like this:

        - shelve://path_to_the_file/file_name
        - json://path_to_the_file/file_name
        - pickle://path_to_the_file/file_name
        - sqlite://path_to_the_file/file_name
        - redis://:pass@localhost:6379/0
        - mongodb://admin:pass@localhost:27017/admin
        - mysql+pymysql://root:pass@localhost:3307/test
        - postgresql://postgres:pass@localhost:5432/test
        - grpc://localhost:2136/local
        - grpcs://localhost:2135/local

    For context storages that write to local files, the function expects a file path instead of connection params:
    json://file.json
    When using sqlite backend your prefix should contain three slashes if you use Windows, or four in other cases.
    sqlite:////file.db
    If you want to use additional parameters in class constructors, you can pass them to this function as kwargs.

    """
    prefix, _, _ = path.partition("://")
    if "sql" in prefix:
        prefix = prefix.split("+")[0]  # this takes care of alternative sql drivers
    assert (
        prefix in PROTOCOLS
    ), f"""
    URI path should be prefixed with one of the following:\n
    {", ".join(PROTOCOLS.keys())}.\n
    For more information, see the function doc:\n{context_storage_factory.__doc__}
    """
    _class, module = PROTOCOLS[prefix]["class"], PROTOCOLS[prefix]["module"]
    target_class = getattr(importlib.import_module(f".{module}", package="dff.context_storages"), _class)
    return target_class(path, **kwargs)
