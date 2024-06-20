from base64 import decodebytes, encodebytes
from copy import deepcopy
from pickle import dumps, loads
from typing import Any, Callable, Dict, List, Union
from typing_extensions import Annotated, TypeAlias
from pydantic import AfterValidator, JsonValue, PlainSerializer, PlainValidator, RootModel, WrapSerializer
from pydantic_core import PydanticSerializationError

_JSON_EXTRA_FIELDS_KEYS = "__pickled_extra_fields__"

Serializable: TypeAlias = Dict[str, Union[JsonValue, Any, List[Any], Dict[str, Any]]]


class WrapperModel(RootModel):
    """
    Wrapper model for testing whether an object is serializable to JSON.
    """

    root: Any


def pickle_serializer(value: Any) -> JsonValue:
    """
    Serializer funtion that serializes any pickle-serializable value into JSON-serializable.
    Serializes value with pickle and encodes bytes as base64 string.

    :param value: Pickle-serializable object.
    :return: String-encoded object.
    """

    return encodebytes(dumps(value)).decode()


def pickle_validator(value: JsonValue) -> Any:
    """
    Validator funtion that validates base64 string encoded bytes as a pickle-serializable value.
    Decodes base64 string and validates value with pickle.

    :param value: String-encoded string.
    :return: Pickle-serializable object.
    """

    return loads(decodebytes(value.encode()))


def json_pickle_serializer(
    model: Serializable, original_serializer: Callable[[Serializable], Serializable]
) -> Serializable:
    """
    Serializer function that serializes a dictionary or Pydantic object to JSON.
    For every object field, it checks whether the field is JSON serializable,
    and if it's not, serializes it using pickle.
    It also keeps track of pickle-serializable field names in a special list.

    :param model: Pydantic model object or a dictionary.
    :original_serializer: Original serializer function for model.
    :return: model with all the fields serialized to JSON.
    """

    extra_fields = list()
    model_copy = deepcopy(model)

    for field_name, field_value in model_copy.items():
        try:
            if isinstance(field_value, bytes):
                raise PydanticSerializationError("")
            else:
                WrapperModel(root=field_value).model_dump_json()
        except PydanticSerializationError:
            model_copy[field_name] = pickle_serializer(field_value)
            extra_fields += [field_name]

    original_dump = original_serializer(model_copy)
    if len(extra_fields) > 0:
        original_dump[_JSON_EXTRA_FIELDS_KEYS] = extra_fields
    return original_dump


def json_pickle_validator(model: Serializable) -> Serializable:
    """
    Validator function that validates a JSON dictionary to a python dictionary.
    For every object field, it checks if the field is pickle-serialized,
    and if it is, validates it using pickle.

    :param model: Pydantic model object or a dictionary.
    :original_serializer: Original serializer function for model.
    :return: model with all the fields serialized to JSON.
    """

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
"""Annotation for field that makes it JSON serializable"""

JSONPickleSerializer = WrapSerializer(json_pickle_serializer, when_used="json")
JSONPickleValidator = AfterValidator(json_pickle_validator)
JSONSerializableDict = Annotated[Serializable, JSONPickleSerializer, JSONPickleValidator]
"""Annotation for dictionary or Pydantic model that makes all its fields JSON serializable"""
