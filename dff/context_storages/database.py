"""
database
---------------------------
| Base module. Provided classes:
| Abstract context storage interface :py:class:`.DBAbstractContextStorage`.
| An intermediate class to inherit from: :py:class:`.DBContextStorage`

"""
import asyncio
import importlib
import threading
from functools import wraps
from abc import ABC, abstractmethod
from typing import Any, Callable

from .protocol import PROTOCOLS
from ..script import Context


class DBAbstractContextStorage(ABC):
    """
    | An abstract interface for DF DB context storages.
    | It includes the most essential methods of the python `dict` class.
    | Can not be instantiated.
    """

    def __init__(self) -> None:
        pass

    def __getitem__(self, key: Any) -> Any:
        return asyncio.run(self.getitem(key))

    @abstractmethod
    async def getitem(self, key: Any) -> Context:
        raise NotImplementedError

    def __setitem__(self, key: Any, value: Context):
        return asyncio.run(self.setitem(key, value))

    @abstractmethod
    async def setitem(self, key: Any, value: Context):
        raise NotImplementedError

    def __delitem__(self, key: str) -> None:
        return asyncio.run(self.delitem(key))

    @abstractmethod
    async def delitem(self, key: str) -> Any:
        raise NotImplementedError

    def __contains__(self, key: str) -> bool:
        return asyncio.run(self.contains(key))

    @abstractmethod
    async def contains(self, key: str) -> Any:
        raise NotImplementedError

    def __len__(self) -> int:
        return asyncio.run(self.len())

    @abstractmethod
    async def len(self) -> Any:
        raise NotImplementedError

    def get(self, key: Any, default=None) -> Any:
        return asyncio.run(self.get_async(key, default))

    @abstractmethod
    async def get_async(self, key: Any, default=None) -> Any:
        raise NotImplementedError

    def clear(self) -> None:
        return asyncio.run(self.clear_async())

    @abstractmethod
    async def clear_async(self) -> Any:
        raise NotImplementedError


class DBContextStorage(DBAbstractContextStorage):
    """
    An intermediate class between the abstract context storage interface,
    :py:class:`.DBAbstractContextStorage`, and concrete implementations.

    Parameters
    ----------
    path: str
        | Parameter `path` should be set with the URI of the database.
        | It includes a prefix and the required connection credentials.
        | Example: postgresql+asyncpg://user:password@host:port/database
        | In the case of classes that save data to hard drive instead of external databases
        | you need to specify the location of the file, like you do in sqlite.
        | Keep in mind that in Windows you will have to use double backslashes '\\'
        | instead of forward slashes '/' when defining the file path.

    """

    def __init__(self, path: str):
        _, _, file_path = path.partition("://")
        self.full_path = path
        self.path = file_path
        self._lock = threading.Lock()

    async def get_async(self, key: Any, default=None):
        key = str(key)
        try:
            return await self.getitem(key)
        except KeyError:
            return default


def threadsafe_method(func: Callable):
    """
    A decorator that makes sure methods of an object instance are threadsafe.
    """

    @wraps(func)
    def _synchronized(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)

    return _synchronized


def context_storage_factory(path: str, **kwargs) -> DBAbstractContextStorage:
    """
    Use context_storage_factory to lazy import context storage types and instantiate them.
    The function takes a database connection URI or its equivalent. It should be prefixed with database name,
    followed by the symbol triplet '://'.
    Then, you should list the connection parameters like this: user:password@host:port/database
    The whole URI will then look like this:
    - shelve://path_to_the_file/file_name
    - json://path_to_the_file/file_name
    - pickle://path_to_the_file/file_name
    - sqlite+aiosqlite://path_to_the_file/file_name
    - redis://:pass@localhost:6379/0
    - mongodb://admin:pass@localhost:27017/admin
    - mysql+asyncmy://root:pass@localhost:3307/test
    - postgresql+asyncpg://postgres:pass@localhost:5432/test
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
