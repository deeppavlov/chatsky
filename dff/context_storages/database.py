"""
Database
--------
The `Database` module provides classes for managing the context storage of a dialog system.
The module can be used to store information such as the current state of the conversation
and other data. This module includes the intermediate class (:py:class:`.DBContextStorage`) is a class
that developers can inherit from in order to create their own context storage solutions.
This class implements the basic functionality and can be extended to add additional features as needed.
"""
import asyncio
import importlib
import threading
from functools import wraps
from abc import ABC, abstractmethod
from typing import Callable, Hashable, Optional

from .protocol import PROTOCOLS
from ..script import Context


class DBContextStorage(ABC):
    r"""
    An abstract interface for `dff` DB context storages.
    It includes the most essential methods of the python `dict` class.
    Can not be instantiated.

    :param path: Parameter `path` should be set with the URI of the database.
        It includes a prefix and the required connection credentials.
        Example: postgresql+asyncpg://user:password@host:port/database
        In the case of classes that save data to hard drive instead of external databases
        you need to specify the location of the file, like you do in sqlite.
        Keep in mind that in Windows you will have to use double backslashes '\\'
        instead of forward slashes '/' when defining the file path.

    """

    def __init__(self, path: str):
        _, _, file_path = path.partition("://")
        self.full_path = path
        """Full path to access the context storage, as it was provided by user."""
        self.path = file_path
        """`full_path` without a prefix defining db used"""
        self._lock = threading.Lock()
        """Threading for methods that require single thread access."""

    def __getitem__(self, key: Hashable) -> Context:
        """
        Synchronous method for accessing stored Context.

        :param key: Hashable key used to store Context instance.
        :return: The stored context, associated with the given key.
        """
        return asyncio.run(self.get_item_async(key))

    @abstractmethod
    async def get_item_async(self, key: Hashable) -> Context:
        """
        Asynchronous method for accessing stored Context.

        :param key: Hashable key used to store Context instance.
        :return: The stored context, associated with the given key.
        """
        raise NotImplementedError

    def __setitem__(self, key: Hashable, value: Context):
        """
        Synchronous method for storing Context.

        :param key: Hashable key used to store Context instance.
        :param value: Context to store.
        """
        return asyncio.run(self.set_item_async(key, value))

    @abstractmethod
    async def set_item_async(self, key: Hashable, value: Context):
        """
        Asynchronous method for storing Context.

        :param key: Hashable key used to store Context instance.
        :param value: Context to store.
        """
        raise NotImplementedError

    def __delitem__(self, key: Hashable):
        """
        Synchronous method for removing stored Context.

        :param key: Hashable key used to identify Context instance for deletion.
        """
        return asyncio.run(self.del_item_async(key))

    @abstractmethod
    async def del_item_async(self, key: Hashable):
        """
        Asynchronous method for removing stored Context.

        :param key: Hashable key used to identify Context instance for deletion.
        """
        raise NotImplementedError

    def __contains__(self, key: Hashable) -> bool:
        """
        Synchronous method for finding whether any Context is stored with given key.

        :param key: Hashable key used to check if Context instance is stored.
        :return: True if there is Context accessible by given key, False otherwise.
        """
        return asyncio.run(self.contains_async(key))

    @abstractmethod
    async def contains_async(self, key: Hashable) -> bool:
        """
        Asynchronous method for finding whether any Context is stored with given key.

        :param key: Hashable key used to check if Context instance is stored.
        :return: True if there is Context accessible by given key, False otherwise.
        """
        raise NotImplementedError

    def __len__(self) -> int:
        """
        Synchronous method for retrieving number of stored Contexts.

        :return: The number of stored Contexts.
        """
        return asyncio.run(self.len_async())

    @abstractmethod
    async def len_async(self) -> int:
        """
        Asynchronous method for retrieving number of stored Contexts.

        :return: The number of stored Contexts.
        """
        raise NotImplementedError

    def get(self, key: Hashable, default: Optional[Context] = None) -> Context:
        """
        Synchronous method for accessing stored Context, returning default if no Context is stored with the given key.

        :param key: Hashable key used to store Context instance.
        :param default: Optional default value to be returned if no Context is found.
        :return: The stored context, associated with the given key or default value.
        """
        return asyncio.run(self.get_async(key, default))

    async def get_async(self, key: Hashable, default: Optional[Context] = None) -> Context:
        """
        Asynchronous method for accessing stored Context, returning default if no Context is stored with the given key.

        :param key: Hashable key used to store Context instance.
        :param default: Optional default value to be returned if no Context is found.
        :return: The stored context, associated with the given key or default value.
        """
        try:
            return await self.get_item_async(str(key))
        except KeyError:
            return default

    def clear(self):
        """
        Synchronous method for clearing context storage, removing all the stored Contexts.
        """
        return asyncio.run(self.clear_async())

    @abstractmethod
    async def clear_async(self):
        """
        Asynchronous method for clearing context storage, removing all the stored Contexts.
        """
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


def context_storage_factory(path: str, **kwargs) -> DBContextStorage:
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
    When using sqlite backend your prefix should contain three slashes if you use Windows, or four in other cases:
    sqlite:////file.db
    If you want to use additional parameters in class constructors, you can pass them to this function as kwargs.

    :param path: Path to the file.
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
