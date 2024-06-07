from base64 import decodebytes, encodebytes
from copy import deepcopy
from pickle import dumps, loads
from typing import Any, Callable
from typing_extensions import Annotated
from pydantic import AfterValidator, JsonValue, PlainSerializer, PlainValidator, PydanticSchemaGenerationError, TypeAdapter, WrapSerializer
from pydantic_core import PydanticSerializationError

_JSON_EXTRA_FIELDS_KEYS = "__pickled_extra_fields__"


def pickle_serializer(value: Any) -> JsonValue:
    return encodebytes(dumps(value)).decode()


def pickle_validator(value: JsonValue) -> Any:
    return loads(decodebytes(value.encode()))


def json_pickle_serializer(model: JsonValue, original_serializer: Callable[[JsonValue], JsonValue]) -> JsonValue:
    extra_fields = list()
    model_copy = deepcopy(model)

    for field_name, field_value in model_copy.items():
        try:
            if isinstance(field_value, bytes):
                raise PydanticSchemaGenerationError("")
            else:
                TypeAdapter(type(field_value))
                model_copy[field_name] = original_serializer(field_value)
        except (PydanticSchemaGenerationError, PydanticSerializationError):
            model_copy[field_name] = pickle_serializer(field_value)
            extra_fields += [field_name]

    original_dump = original_serializer(model_copy)
    original_dump[_JSON_EXTRA_FIELDS_KEYS] = extra_fields
    return original_dump


def json_pickle_validator(model: JsonValue) -> JsonValue:
    model_copy = deepcopy(model)

    if _JSON_EXTRA_FIELDS_KEYS in model.keys():
        for extra_key in model[_JSON_EXTRA_FIELDS_KEYS]:
            extra_value = model[extra_key]
            model_copy[extra_key] = pickle_validator(extra_value)
        del model_copy[_JSON_EXTRA_FIELDS_KEYS]

    return model_copy


PickleSerializer = PlainSerializer(pickle_serializer, when_used="json")
PickleValidator = PlainValidator(pickle_validator)
SerializableVaue = Annotated[Any, PickleSerializer, PickleValidator]

JSONPickleSerializer = WrapSerializer(json_pickle_serializer, when_used="json")
JSONPickleValidator = AfterValidator(json_pickle_validator)
JSONSerializableDict = Annotated[JsonValue, JSONPickleSerializer, JSONPickleValidator]
