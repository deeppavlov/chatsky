from abc import ABC, abstractmethod
from json import loads as load_json, dumps as dumps_json
from pickle import loads as load_pickle, dumps as dumps_pickle
from typing import Any, Dict

class BaseSerializer(ABC):
    @abstractmethod
    def loads(self, data: bytes) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def dumps(self, data: Dict[str, Any]) -> bytes:
        raise NotImplementedError


class PickleSerializer(BaseSerializer):
    def loads(self, data: bytes) -> Dict[str, Any]:
        return load_pickle(data)
    
    def dumps(self, data: Dict[str, Any]) -> bytes:
        return dumps_pickle(data)


class JsonSerializer:
    def loads(self, data: bytes) -> Dict[str, Any]:
        return load_json(data.decode("utf-8"))
    
    def dumps(self, data: Dict[str, Any]) -> bytes:
        return dumps_json(data).encode("utf-8")
