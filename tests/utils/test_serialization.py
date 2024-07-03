from typing import Optional

import pytest
from pydantic import BaseModel
from copy import deepcopy

import chatsky.utils.devel.json_serialization as json_ser


class UnserializableClass:
    def __init__(self):
        self.exc = RuntimeError("exception")

    def __eq__(self, other):
        if not isinstance(other, UnserializableClass):
            return False
        return type(self.exc) == type(other.exc) and self.exc.args == other.exc.args  # noqa: E721


class PydanticClass(BaseModel, arbitrary_types_allowed=True):
    field: Optional[UnserializableClass]


class TestJSONPickleSerialization:
    @pytest.fixture(scope="function")
    def unserializable_obj(self):
        return UnserializableClass()

    #########################
    # DICT-RELATED FIXTURES #
    #########################

    @pytest.fixture(scope="function")
    def unserializable_dict(self, unserializable_obj):
        return {
            "bytes": b"123",
            "non_pydantic_non_serializable": unserializable_obj,
            "non_pydantic_serializable": "string",
            "pydantic_non_serializable": PydanticClass(field=unserializable_obj),
            "pydantic_serializable": PydanticClass(field=None),
        }

    @pytest.fixture(scope="function")
    def non_serializable_fields(self):
        return ["bytes", "non_pydantic_non_serializable", "pydantic_non_serializable"]

    @pytest.fixture(scope="function")
    def deserialized_dict(self, unserializable_obj):
        return {
            "bytes": b"123",
            "non_pydantic_non_serializable": unserializable_obj,
            "non_pydantic_serializable": "string",
            "pydantic_non_serializable": PydanticClass(field=unserializable_obj),
            "pydantic_serializable": {"field": None},
        }

    #########################
    #########################
    #########################

    def test_pickle(self, unserializable_obj):
        serialized = json_ser.pickle_serializer(unserializable_obj)
        assert isinstance(serialized, str)
        assert json_ser.pickle_validator(serialized) == unserializable_obj

    def test_json_pickle(self, unserializable_dict, non_serializable_fields, deserialized_dict):
        dict_copy = deepcopy(unserializable_dict)

        serialized = json_ser.json_pickle_serializer(dict_copy)

        assert dict_copy == unserializable_dict, "Dict changed by serializer"

        assert serialized[json_ser._JSON_EXTRA_FIELDS_KEYS] == non_serializable_fields
        assert all(isinstance(serialized[field], str) for field in non_serializable_fields)
        assert serialized["non_pydantic_serializable"] == "string"
        assert serialized["pydantic_serializable"] == {"field": None}

        deserialized = json_ser.json_pickle_validator(serialized)
        assert deserialized == deserialized_dict

    def test_serializable_value(self, unserializable_obj):
        class Class(BaseModel):
            field: Optional[json_ser.PickleEncodedValue] = None

        obj = Class()
        obj.field = unserializable_obj

        obj_copy = obj.model_copy(deep=True)

        dump = obj_copy.model_dump(mode="json")

        assert obj == obj_copy, "Object changed by serializer"

        assert isinstance(dump["field"], str)

        reconstructed_obj = Class.model_validate(dump)

        assert reconstructed_obj.field == unserializable_obj

    def test_serializable_dict(self, unserializable_dict, non_serializable_fields, deserialized_dict):
        class Class(BaseModel):
            field: json_ser.JSONSerializableDict

        obj = Class(field=unserializable_dict)

        obj_copy = obj.model_copy(deep=True)

        dump = obj_copy.model_dump(mode="json")

        assert obj == obj_copy, "Object changed by serializer"

        assert dump["field"][json_ser._JSON_EXTRA_FIELDS_KEYS] == non_serializable_fields

        reconstructed_obj = Class.model_validate(dump)

        assert reconstructed_obj.field == deserialized_dict

    def test_serializable_extras(self, unserializable_dict, non_serializable_fields, deserialized_dict):
        class Class(json_ser.JSONSerializableExtras):
            pass

        obj = Class(**unserializable_dict)

        obj_copy = obj.model_copy(deep=True)

        dump = obj_copy.model_dump(mode="json")

        assert obj == obj_copy, "Object changed by serializer"

        assert dump[json_ser._JSON_EXTRA_FIELDS_KEYS] == non_serializable_fields

        reconstructed_obj = Class.model_validate(dump)

        assert reconstructed_obj.__pydantic_extra__ == deserialized_dict
