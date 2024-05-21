from base64 import decodebytes, encodebytes
from copy import deepcopy
from pickle import dumps, loads
from typing import Annotated, Any, Callable, Dict
from pydantic import PydanticSchemaGenerationError, TypeAdapter, WrapSerializer, WrapValidator

_JSON_EXTRA_FIELDS_KEYS = "__pickled_extra_fields__"


def json_pickle_serializer(model: Dict[str, Any], original_serializer: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    extra_fields = list()
    model_copy = deepcopy(model)

    for field_name, field_value in model_copy.items():
        try:
            if isinstance(field_value, bytes):
                raise PydanticSchemaGenerationError("")
            else:
                TypeAdapter(type(field_value))
        except PydanticSchemaGenerationError:
            model_copy[field_name] = encodebytes(dumps(field_value)).decode()
            extra_fields += [field_name]

    original_dump = original_serializer(model_copy)
    original_dump[_JSON_EXTRA_FIELDS_KEYS] = extra_fields
    return original_dump


def json_pickle_validator(model: Dict[str, Any]) -> Dict[str, Any]:
    model_copy = deepcopy(model)

    if _JSON_EXTRA_FIELDS_KEYS in model.keys():
        for extra_key in model[_JSON_EXTRA_FIELDS_KEYS]:
            extra_value = model[extra_key]
            model_copy[extra_key] = loads(decodebytes(extra_value.encode()))
        del model_copy[_JSON_EXTRA_FIELDS_KEYS]

    return model_copy


JSONPickleSerializer = WrapSerializer(json_pickle_serializer, when_used="json")
JSONPickleValidator = WrapValidator(json_pickle_validator)
JSONSerializableDict = Annotated[Dict[str, Any], JSONPickleSerializer, JSONPickleValidator]
