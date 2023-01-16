"""
Database
--------
Base module. Provided classes:
    - Abstract context storage interface :py:class:`.DBAbstractContextStorage`.
"""
import asyncio
import importlib
import threading
from functools import wraps
from abc import ABC, abstractmethod
from typing import Callable, Hashable, Optional

from .protocol import PROTOCOLS
from ..script import Context


class DBAbstractContextStorage(ABC):
    """
    An abstract interface for `dff` DB context storages.
    It includes the most essential methods of the python `dict` class.
    Can not be instantiated.

    Parameters
    ----------
    : param path:
        | Parameter `path` should be set with the URI of the database.
        | It includes a prefix and the required connection credentials.
        | Example: postgresql+asyncpg://user:password@host:port/database
        | In the case of classes that save data to hard drive instead of external databases
        | you need to specify the location of the file, like you do in sqlite.
        | Keep in mind that in Windows you will have to use double backslashes '\\'
        | instead of forward slashes '/' when defining the file path.
    :type path: str

    """

    def __init__(self, path: str):
        _, _, file_path = path.partition("://")
        self.full_path = path
        self.path = file_path
        self._lock = threading.Lock()

    def __getitem__(self, key: Hashable) -> Context:
        return asyncio.run(self.getitem_async(key))

    @abstractmethod
    async def getitem_async(self, key: Hashable) -> Context:
        raise NotImplementedError

    def __setitem__(self, key: Hashable, value: Context):
        return asyncio.run(self.setitem_async(key, value))

    @abstractmethod
    async def setitem_async(self, key: Hashable, value: Context):
        raise NotImplementedError

    def __delitem__(self, key: Hashable):
        return asyncio.run(self.delitem_async(key))

    @abstractmethod
    async def delitem_async(self, key: Hashable):
        raise NotImplementedError

    def __contains__(self, key: Hashable) -> bool:
        return asyncio.run(self.contains_async(key))

    @abstractmethod
    async def contains_async(self, key: Hashable) -> bool:
        raise NotImplementedError

    def __len__(self) -> int:
        return asyncio.run(self.len_async())

    @abstractmethod
    async def len_async(self) -> int:
        raise NotImplementedError

    def get(self, key: Hashable, default: Optional[Context] = None) -> Context:
        return asyncio.run(self.get_async(key, default))

    async def get_async(self, key: Hashable, default: Optional[Context] = None) -> Context:
        try:
            return await self.getitem_async(str(key))
        except KeyError:
            return default

    def clear(self):
        return asyncio.run(self.clear_async())

    @abstractmethod
    async def clear_async(self):
        raise NotImplementedError


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
    - redis://:pass@localhost:6378/0
    - mongodb://admin:pass@localhost:27016/admin
    - mysql+asyncmy://root:pass@localhost:3306/test
    - postgresql+asyncpg://postgres:pass@localhost:5430/test
    - grpc://localhost:2134/local
    - grpcs://localhost:2134/local

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
