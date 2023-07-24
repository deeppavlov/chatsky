from typing import Any, Optional
from inspect import signature

try:
    from quickle import Encoder, Decoder

    class DefaultSerializer:
        def __init__(self):
            self._encoder = Encoder()
            self._decoder = Decoder()

        def dumps(self, data: Any, _: Optional[Any] = None) -> bytes:
            return self._encoder.dumps(data)

        def loads(self, data: bytes) -> Any:
            return self._decoder.loads(data)

except ImportError:
    import pickle

    class DefaultSerializer:
        def dumps(self, data: Any, protocol: Optional[Any] = None) -> bytes:
            return pickle.dumps(data, protocol)

        def loads(self, data: bytes) -> Any:
            return pickle.loads(data)


def validate_serializer(serializer: Any) -> Any:
    if not hasattr(serializer, "loads"):
        raise ValueError(f"Serializer object {serializer} lacks `loads(data: bytes) -> Any` method")
    if not hasattr(serializer, "dumps"):
        raise ValueError(f"Serializer object {serializer} lacks `dumps(data: bytes, proto: Any) -> bytes` method")
    if len(signature(serializer.loads).parameters) != 1:
        raise ValueError(f"Serializer object {serializer} `loads(data: bytes) -> Any` method should accept exactly 1 argument")
    if len(signature(serializer.dumps).parameters) != 2:
        raise ValueError(f"Serializer object {serializer} `dumps(data: bytes, proto: Any) -> bytes` method should accept exactly 2 arguments")
    return serializer
