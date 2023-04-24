import time
from hashlib import sha256
from enum import Enum, auto
from pydantic import BaseModel, validator, root_validator
from pydantic.typing import ClassVar
from typing import Dict, List, Optional, Tuple, Iterable, Callable, Any, Union, Awaitable, Hashable

from dff.script import Context

ALL_ITEMS = "__all__"


class OutlookType(Enum):
    SLICE = auto()
    KEYS = auto()
    NONE = auto()


class FieldType(Enum):
    LIST = auto()
    DICT = auto()
    VALUE = auto()


_ReadKeys = Dict[str, List[str]]
_ReadContextFunction = Callable[[Dict[str, Union[bool, Dict[Hashable, bool]]], str, str], Awaitable[Dict]]
_WriteContextFunction = Callable[[Dict[str, Any], str, str], Awaitable]


class FieldRule(str, Enum):
    READ = "read"
    IGNORE = "ignore"
    UPDATE = "update"
    HASH_UPDATE = "hash_update"
    UPDATE_ONCE = "update_once"
    APPEND = "append"


UpdateSchemeBuilder = Dict[str, Union[Tuple[str], Tuple[str, str]]]


class ExtraFields(BaseModel):
    IDENTITY_FIELD: ClassVar = "id"
    EXTERNAL_FIELD: ClassVar = "ext_id"
    CREATED_AT_FIELD: ClassVar = "created_at"
    UPDATED_AT_FIELD: ClassVar = "updated_at"


class SchemaField(BaseModel):
    name: str
    field_type: FieldType = FieldType.VALUE
    on_read: FieldRule = FieldRule.IGNORE
    on_write: FieldRule = FieldRule.IGNORE
    outlook_type: OutlookType = OutlookType.NONE
    outlook: Optional[Union[str, List[Any]]] = None

    @root_validator(pre=True)
    def set_default_outlook(cls, values: dict) -> dict:
        field_type: FieldType = values.get("field_type")
        field_name: str = values.get("field_name")
        outlook = values.get("outlook")
        if not outlook:
            if field_type == FieldType.LIST:
                values.update({"outlook": "[:]"})
            elif field_type == FieldType.DICT:
                values.update({"outlook": "[all]"})
        else:
            if field_type == FieldType.VALUE:
                raise RuntimeError(
                    f"Field '{field_name}' shouldn't have an outlook value - it is of type '{field_type}'!"
                )
        return values

    @root_validator(pre=True)
    def validate_outlook_type(cls, values: dict) -> dict:
        outlook = values.get("outlook")
        field_type = values.get("field_type")
        if field_type == FieldType.DICT:
            values.update({"outlook_type": OutlookType.KEYS})
        if field_type == FieldType.LIST:
            if ":" in outlook:
                values.update({"outlook_type": OutlookType.SLICE})
            else:
                values.update({"outlook_type ": OutlookType.KEYS})
        return values

    @validator("on_write")
    def validate_write(cls, value: FieldRule, values: dict):
        field_type = values.get("field_type")
        field_name = values.get("name")
        list_write_wrong_rule = field_type == FieldType.LIST and (
            value == FieldRule.UPDATE or value == FieldRule.HASH_UPDATE
        )
        field_write_wrong_rule = field_type != FieldType.LIST and value == FieldRule.APPEND
        if list_write_wrong_rule or field_write_wrong_rule:
            raise Exception(f"Write rule '{value}' not defined for field '{field_name}' of type '{field_type}'!")
        return value

    @validator("outlook", always=True)
    def validate_outlook(cls, value: Optional[Union[str, List[Any]]], values: dict) -> Optional[List[Any]]:
        field_type: FieldType = values.get("field_type")
        outlook_type: OutlookType = values.get("outlook_type")
        field_name: str = values.get("field_name")
        if outlook_type == OutlookType.SLICE:
            value = value.strip("[]").split(":")
            if len(value) != 2:
                raise Exception(f"For outlook of type `slice` use colon-separated offset and limit integers.")
            else:
                value = [int(item) for item in [value[0] or 0, value[1] or -1]]
        elif outlook_type == OutlookType.KEYS:
            try:
                value = eval(value, {}, {"all": ALL_ITEMS})
            except Exception as e:
                raise Exception(f"While parsing outlook of field '{field_name}' exception happened: {e}")
            if not isinstance(value, List):
                raise Exception(
                    f"Outlook of field '{field_name}' exception isn't a list - it is of type '{field_type}'!"
                )
            if field_type == FieldType.DICT and ALL_ITEMS in value and len(value) > 1:
                raise Exception(f"Element 'all' should be the only element of the outlook of the field '{field_name}'!")
            if field_type == FieldType.LIST and not all([isinstance(item, int) for item in value]):
                raise Exception(f"Outlook of field '{field_name}' contains non-integer values!")
        return value

    @classmethod
    def from_dict_item(cls, item: tuple):
        return cls(name=item[0], **item[1])


default_update_scheme = {
    "id": {"offset": None, "field_type": FieldType.VALUE, "on_read": "read"},
    "requests": {"offset": "[-1]", "field_type": FieldType.LIST, "on_read": "read", "on_write": "append"},
    "responses": {"offset": "[-1]", "field_type": FieldType.LIST, "on_read": "read", "on_write": "append"},
    "labels": {"offset": "[-1]", "field_type": FieldType.LIST, "on_read": "read", "on_write": "append"},
    "misc": {"offset": "[all]", "field_type": FieldType.DICT, "on_read": "read", "on_write": "update"},
    "framework_states": {"offset": "[all]", "field_type": FieldType.DICT, "on_read": "read", "on_write": "update"},
}

full_update_scheme = {
    "id": {"offset": None, "field_type": FieldType.VALUE, "on_read": "read"},
    "requests": {"offset": "[:]", "field_type": FieldType.LIST, "on_read": "read", "on_write": "append"},
    "responses": {"offset": "[:]", "field_type": FieldType.LIST, "on_read": "read", "on_write": "append"},
    "labels": {"offset": "[:]", "field_type": FieldType.LIST, "on_read": "read", "on_write": "append"},
    "misc": {"offset": "[all]", "field_type": FieldType.DICT, "on_read": "read", "on_write": "update"},
    "framework_states": {"offset": "[all]", "field_type": FieldType.DICT, "on_read": "read", "on_write": "update"},
}


class UpdateScheme(BaseModel):
    EXTRA_FIELDS: ClassVar = [getattr(ExtraFields, item) for item in ExtraFields.__class_vars__]
    ALL_FIELDS: ClassVar = set(EXTRA_FIELDS + list(Context.__fields__.keys()))
    fields: Dict[str, SchemaField]

    @classmethod
    def from_dict_schema(cls, dict_schema: UpdateSchemeBuilder = default_update_scheme):
        schema = {name: {} for name in cls.ALL_FIELDS}
        schema.update(dict_schema)
        fields = {name: SchemaField.from_dict_item((name, props)) for name, props in schema.items()}
        return cls(fields=fields)

    def mark_db_not_persistent(self):
        for field in self.fields.values():
            if field.on_write in (FieldRule.HASH_UPDATE, FieldRule.UPDATE_ONCE, FieldRule.APPEND):
                field.on_write = FieldRule.UPDATE

    @staticmethod
    def _get_update_field(dictionary_keys: Iterable, outlook: List, outlook_type: OutlookType) -> List:
        if outlook_type == OutlookType.KEYS:
            list_keys = sorted(list(dictionary_keys))
            if len(list_keys) < 0:
                return []
            return list_keys[outlook[0] : min(outlook[1], len(list_keys))]
        else:
            list_keys = sorted(list(dictionary_keys))
            return [list_keys[key] for key in outlook] if len(list_keys) > 0 else list()

    def _update_hashes(self, value: Union[Dict[str, Any], Any], field: str, hashes: Dict[str, Any]):
        if self.fields[field].on_write == FieldRule.HASH_UPDATE:
            if isinstance(value, dict):
                hashes[field] = {k: sha256(str(v).encode("utf-8")) for k, v in value.items()}
            else:
                hashes[field] = sha256(str(value).encode("utf-8"))

    async def read_context(
        self, fields: _ReadKeys, ctx_reader: _ReadContextFunction, ext_id: str, int_id: str
    ) -> Tuple[Context, Dict]:
        fields_outlook = dict()
        for field, field_props in self.fields.items():
            if field_props.on_read == FieldRule.IGNORE:
                fields_outlook[field] = False
            elif field_props.field_type == FieldType.LIST:
                list_keys = fields.get(field, list())
                update_field = self._get_update_field(list_keys, field_props.outlook, field_props.outlook_type)
                fields_outlook[field] = {field: True for field in update_field}
            elif field_props.field_type == FieldType.DICT:
                update_field = field_props.outlook
                if ALL_ITEMS in update_field:
                    update_field = fields.get(field, list())
                fields_outlook[field] = {field: True for field in update_field}
            else:
                fields_outlook[field] = True

        hashes = dict()
        ctx_dict = await ctx_reader(fields_outlook, int_id, ext_id)
        for field in self.fields.keys():
            if ctx_dict.get(field, None) is None:
                if field == ExtraFields.IDENTITY_FIELD:
                    ctx_dict[field] = int_id
                elif field == ExtraFields.EXTERNAL_FIELD:
                    ctx_dict[field] = ext_id
            if ctx_dict.get(field, None) is not None:
                self._update_hashes(ctx_dict[field], field, hashes)

        return Context.cast(ctx_dict), hashes

    async def write_context(
        self, ctx: Context, hashes: Optional[Dict], fields: _ReadKeys, val_writer: _WriteContextFunction, ext_id: str
    ):
        ctx_dict = ctx.dict()
        ctx_dict[ExtraFields.EXTERNAL_FIELD] = str(ext_id)
        ctx_dict[ExtraFields.CREATED_AT_FIELD] = ctx_dict[ExtraFields.UPDATED_AT_FIELD] = time.time_ns()

        patch_dict = dict()
        for field, field_props in self.fields.items():
            if field_props.on_write == FieldRule.IGNORE:
                continue
            elif field_props.on_write == FieldRule.UPDATE_ONCE and hashes is not None:
                continue

            elif field_props.field_type == FieldType.LIST:
                list_keys = fields.get(field, list())
                update_field = self._get_update_field(
                    ctx_dict[field].keys(), field_props.outlook, field_props.outlook_type
                )
                if field_props.on_write == FieldRule.APPEND:
                    patch_dict[field] = {item: ctx_dict[field][item] for item in set(update_field) - set(list_keys)}
                else:
                    patch_dict[field] = {item: ctx_dict[field][item] for item in update_field}

            elif field_props.field_type == FieldType.DICT:
                list_keys = fields.get(field, list())
                update_field = field_props.outlook
                update_keys_all = list_keys + list(ctx_dict[field].keys())
                update_keys = set(update_keys_all if ALL_ITEMS in update_field else update_field)

                if field_props.on_write == FieldRule.HASH_UPDATE:
                    patch_dict[field] = dict()
                    for item in update_keys:
                        item_hash = sha256(str(ctx_dict[field][item]).encode("utf-8"))
                        if hashes is None or hashes.get(field, dict()).get(item, None) != item_hash:
                            patch_dict[field][item] = ctx_dict[field][item]
                else:
                    patch_dict[field] = {item: ctx_dict[field][item] for item in update_keys}
            else:
                patch_dict[field] = ctx_dict[field]

        await val_writer(patch_dict, ctx.id, ext_id)
