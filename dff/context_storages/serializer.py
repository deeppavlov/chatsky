"""
Serializer
----------
Serializer is an interface that will be used for data storing in various databases.
Many libraries already support this interface (built-in jsin, pickle and other 3rd party libs).
All other libraries will have to implement the two (loads and dumps) required methods.
A custom serializer class can be created using :py:class:`~.DefaultSerializer` as a template or parent.
Default serializer uses built-in `pickle` module.
"""

from typing import Any, Optional
from inspect import signature

import pickle


class DefaultSerializer:
    """
    This default serializer uses `pickle` module for serialization.
    """

    def dumps(self, data: Any, protocol: Optional[Any] = None) -> bytes:
        return pickle.dumps(data, protocol)

    def loads(self, data: bytes) -> Any:
        return pickle.loads(data)


def validate_serializer(serializer: Any) -> Any:
    """
    Check if serializer object has required functions and they accept required arguments.
    Any serializer should have these two methods:

    1. `loads(data: bytes) -> Any`: deserialization method, accepts bytes object and returns
        serialized data.
    2. `dumps(data: bytes, proto: Any)`: serialization method, accepts anything and returns
        serialized bytes data.

    :param serializer: An object to check.

    :raise ValueError: Exception will be raised if the object is not a valid serializer.

    :return: the serializer if it is a valid serializer.
    """
    if not hasattr(serializer, "loads"):
        raise ValueError(f"Serializer object {serializer} lacks `loads(data: bytes) -> Any` method")
    if not hasattr(serializer, "dumps"):
        raise ValueError(f"Serializer object {serializer} lacks `dumps(data: bytes, proto: Any) -> bytes` method")
    if len(signature(serializer.loads).parameters) != 1:
        raise ValueError(
            f"Serializer object {serializer} `loads(data: bytes) -> Any` method should accept exactly 1 argument"
        )
    if len(signature(serializer.dumps).parameters) != 2:
        raise ValueError(
            f"Serializer object {serializer} `dumps(data: bytes, proto: Any) -> bytes` "
            "method should accept exactly 2 arguments"
        )
    return serializer
