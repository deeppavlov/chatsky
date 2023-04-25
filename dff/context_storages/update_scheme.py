import time
from hashlib import sha256
from enum import Enum, auto
from pydantic import BaseModel, validator, root_validator, Field
from pydantic.typing import Literal
from typing import Dict, List, Optional, Tuple, Iterable, Callable, Any, Union, Awaitable, Hashable

from dff.script import Context

ALL_ITEMS = "__all__"


class OutlookType(Enum):
    SLICE = auto()
    KEYS = auto()
    NONE = auto()


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


class BaseSchemaField(BaseModel):
    name: str
    on_read: Literal[FieldRule.READ, FieldRule.IGNORE] = FieldRule.READ
    on_write: FieldRule = FieldRule.IGNORE
    outlook_type: OutlookType = OutlookType.NONE
    outlook: Union[str, List[Any], None] = None

    @validator("outlook", always=True)
    def parse_keys_outlook(cls, value, values: dict):
        field_name: str = values.get("name")
        outlook_type: OutlookType = values.get("outlook_type")
        if outlook_type == OutlookType.KEYS and isinstance(value, str):
            try:
                value = eval(value, {}, {"all": ALL_ITEMS})
            except Exception as e:
                raise Exception(f"While parsing outlook of field '{field_name}' exception happened: {e}")
            if not isinstance(value, List):
                raise Exception(f"Outlook of field '{field_name}' exception isn't a list'!")
            if ALL_ITEMS in value and len(value) > 1:
                raise Exception(f"Element 'all' should be the only element of the outlook of the field '{field_name}'!")
        return value


class ListField(BaseSchemaField):
    on_write: Literal[FieldRule.IGNORE, FieldRule.APPEND, FieldRule.UPDATE_ONCE] = FieldRule.APPEND
    outlook_type: Literal[OutlookType.KEYS, OutlookType.SLICE] = OutlookType.SLICE
    outlook: Union[str, List[Any]] = "[:]"

    @root_validator()
    def infer_outlook_type(cls, values: dict) -> dict:
        outlook = values.get("outlook") or "[:]"
        if isinstance(outlook, str) and ":" in outlook:
            values.update({"outlook_type": OutlookType.SLICE, "outlook": outlook})
        else:
            values.update({"outlook_type ": OutlookType.KEYS, "outlook": outlook})
        return values

    @validator("outlook", always=True)
    def parse_slice_outlook(cls, value, values: dict):
        field_name: str = values.get("field_name")
        outlook_type: OutlookType = values.get("outlook_type")
        if outlook_type == OutlookType.SLICE and isinstance(value, str):
            value = value.strip("[]").split(":")
            if len(value) != 2:
                raise Exception("For outlook of type `slice` use colon-separated offset and limit integers.")
            else:
                value = [int(item) for item in [value[0] or 0, value[1] or -1]]
        if not all([isinstance(item, int) for item in value]):
            raise Exception(f"Outlook of field '{field_name}' contains non-integer values!")
        return value


class DictField(BaseSchemaField):
    on_write: Literal[
        FieldRule.IGNORE, FieldRule.UPDATE, FieldRule.HASH_UPDATE, FieldRule.UPDATE_ONCE
    ] = FieldRule.UPDATE
    outlook_type: Literal[OutlookType.KEYS] = Field(OutlookType.KEYS, const=True)
    outlook: Union[str, List[Any]] = "[all]"


class ValueField(BaseSchemaField):
    on_write: Literal[
        FieldRule.IGNORE, FieldRule.UPDATE, FieldRule.HASH_UPDATE, FieldRule.UPDATE_ONCE
    ] = FieldRule.IGNORE
    outlook_type: Literal[OutlookType.NONE] = Field(OutlookType.NONE, const=True)
    outlook: Literal[None] = Field(None, const=True)


class ExtraFields(str, Enum):
    id = "id"
    ext_id = "ext_id"
    created_at = "created_at"
    updated_at = "updated_at"


class UpdateScheme(BaseModel):
    id: ValueField = ValueField(name=ExtraFields.id)
    requests: ListField = ListField(name="requests")
    responses: ListField = ListField(name="responses")
    labels: ListField = ListField(name="labels")
    misc: DictField = DictField(name="misc")
    framework_states: DictField = DictField(name="framework_states")
    ext_id: ValueField = ValueField(name=ExtraFields.ext_id)
    created_at: ValueField = ValueField(name=ExtraFields.created_at)
    updated_at: ValueField = ValueField(name=ExtraFields.updated_at)

    def mark_db_not_persistent(self):
        for field, field_props in dict(self).items():
            if field_props.on_write in (FieldRule.HASH_UPDATE, FieldRule.UPDATE_ONCE, FieldRule.APPEND):
                field_props.on_write = FieldRule.UPDATE
                setattr(self, field, field_props)

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
        if getattr(self, field).on_write == FieldRule.HASH_UPDATE:
            if isinstance(value, dict):
                hashes[field] = {k: sha256(str(v).encode("utf-8")) for k, v in value.items()}
            else:
                hashes[field] = sha256(str(value).encode("utf-8"))

    async def read_context(
        self, fields: _ReadKeys, ctx_reader: _ReadContextFunction, ext_id: str, int_id: str
    ) -> Tuple[Context, Dict]:
        fields_outlook = dict()
        field_props: BaseSchemaField
        for field, field_props in dict(self).items():
            if field_props.on_read == FieldRule.IGNORE:
                fields_outlook[field] = False
            elif isinstance(field_props, ListField):
                list_keys = fields.get(field, list())
                update_field = self._get_update_field(list_keys, field_props.outlook, field_props.outlook_type)
                fields_outlook[field] = {field: True for field in update_field}
            elif isinstance(field_props, DictField):
                update_field = field_props.outlook
                if ALL_ITEMS in update_field:
                    update_field = fields.get(field, list())
                fields_outlook[field] = {field: True for field in update_field}
            else:
                fields_outlook[field] = True

        hashes = dict()
        ctx_dict = await ctx_reader(fields_outlook, int_id, ext_id)
        for field in self.dict():
            if ctx_dict.get(field, None) is None:
                if field == ExtraFields.id:
                    ctx_dict[field] = int_id
                elif field == ExtraFields.ext_id:
                    ctx_dict[field] = ext_id
            if ctx_dict.get(field, None) is not None:
                self._update_hashes(ctx_dict[field], field, hashes)

        return Context.cast(ctx_dict), hashes

    async def write_context(
        self, ctx: Context, hashes: Optional[Dict], fields: _ReadKeys, val_writer: _WriteContextFunction, ext_id: str
    ):
        ctx_dict = ctx.dict()
        ctx_dict[self.ext_id.name] = str(ext_id)
        ctx_dict[self.created_at.name] = ctx_dict[self.updated_at.name] = time.time_ns()

        patch_dict = dict()
        field_props: BaseSchemaField
        for field, field_props in dict(self).items():
            if field_props.on_write == FieldRule.IGNORE:
                continue
            elif field_props.on_write == FieldRule.UPDATE_ONCE and hashes is not None:
                continue

            elif isinstance(field_props, ListField):
                list_keys = fields.get(field, list())
                update_field = self._get_update_field(
                    ctx_dict[field].keys(), field_props.outlook, field_props.outlook_type
                )
                if field_props.on_write == FieldRule.APPEND:
                    patch_dict[field] = {item: ctx_dict[field][item] for item in set(update_field) - set(list_keys)}
                else:
                    patch_dict[field] = {item: ctx_dict[field][item] for item in update_field}

            elif isinstance(field_props, DictField):
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
