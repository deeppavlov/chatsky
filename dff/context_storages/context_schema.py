import time
from hashlib import sha256
from enum import Enum, auto
from pydantic import BaseModel, validator, root_validator, Field
from pydantic.typing import Literal
from typing import Dict, List, Optional, Tuple, Iterable, Callable, Any, Union, Awaitable, Hashable

from dff.script import Context

ALL_ITEMS = "__all__"


class SubscriptType(Enum):
    SLICE = auto()
    KEYS = auto()
    NONE = auto()


_ReadKeys = Dict[str, List[str]]
_ReadContextFunction = Callable[[Dict[str, Union[bool, Dict[Hashable, bool]]], str, str], Awaitable[Dict]]
_WriteContextFunction = Callable[[Dict[str, Any], str, str], Awaitable]


class SchemaFieldReadPolicy(str, Enum):
    READ = "read"
    IGNORE = "ignore"


class SchemaFieldWritePolicy(str, Enum):
    IGNORE = "ignore"
    UPDATE = "update"
    HASH_UPDATE = "hash_update"
    UPDATE_ONCE = "update_once"
    APPEND = "append"


class BaseSchemaField(BaseModel):
    name: str
    on_read: SchemaFieldReadPolicy = SchemaFieldReadPolicy.READ
    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.IGNORE
    subscript_type: SubscriptType = SubscriptType.NONE
    subscript: Optional[Union[str, List[Any]]] = None

    @validator("subscript", always=True)
    def parse_keys_subscript(cls, value, values: dict):
        field_name: str = values.get("name")
        subscript_type: SubscriptType = values.get("subscript_type")
        if subscript_type == SubscriptType.KEYS:
            if isinstance(value, str):
                try:
                    value = eval(value, {}, {"all": ALL_ITEMS})
                except Exception as e:
                    raise Exception(f"While parsing subscript of field '{field_name}' exception happened: {e}")
            if not isinstance(value, List):
                raise Exception(f"subscript of field '{field_name}' exception isn't a list'!")
            if ALL_ITEMS in value and len(value) > 1:
                raise Exception(
                    f"Element 'all' should be the only element of the subscript of the field '{field_name}'!"
                )
        return value


class ListSchemaField(BaseSchemaField):
    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.APPEND
    subscript_type: Literal[SubscriptType.KEYS, SubscriptType.SLICE] = SubscriptType.SLICE
    subscript: Union[str, List[Any]] = "[:]"

    @root_validator()
    def infer_subscript_type(cls, values: dict) -> dict:
        subscript = values.get("subscript") or "[:]"
        if isinstance(subscript, str) and ":" in subscript:
            values.update({"subscript_type": SubscriptType.SLICE, "subscript": subscript})
        else:
            values.update({"subscript_type ": SubscriptType.KEYS, "subscript": subscript})
        return values

    @validator("subscript", always=True)
    def parse_slice_subscript(cls, value, values: dict):
        field_name: str = values.get("field_name")
        subscript_type: SubscriptType = values.get("subscript_type")
        if subscript_type == SubscriptType.SLICE and isinstance(value, str):
            value = value.strip("[]").split(":")
            if len(value) != 2:
                raise Exception("For subscript of type `slice` use colon-separated offset and limit integers.")
            else:
                value = [int(item) for item in [value[0] or 0, value[1] or -1]]
        if not all([isinstance(item, int) for item in value]):
            raise Exception(f"subscript of field '{field_name}' contains non-integer values!")
        return value


class DictSchemaField(BaseSchemaField):
    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.UPDATE
    subscript_type: Literal[SubscriptType.KEYS] = Field(SubscriptType.KEYS, const=True)
    subscript: Union[str, List[Any]] = "[all]"


class ValueSchemaField(BaseSchemaField):
    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.IGNORE
    subscript_type: Literal[SubscriptType.NONE] = Field(SubscriptType.NONE, const=True)
    subscript: Literal[None] = Field(None, const=True)


class ExtraFields(str, Enum):
    id = "id"
    ext_id = "ext_id"
    created_at = "created_at"
    updated_at = "updated_at"


class ContextSchema(BaseModel):
    id: ValueSchemaField = ValueSchemaField(name=ExtraFields.id)
    requests: ListSchemaField = ListSchemaField(name="requests")
    responses: ListSchemaField = ListSchemaField(name="responses")
    labels: ListSchemaField = ListSchemaField(name="labels")
    misc: DictSchemaField = DictSchemaField(name="misc")
    framework_states: DictSchemaField = DictSchemaField(name="framework_states")
    ext_id: ValueSchemaField = ValueSchemaField(name=ExtraFields.ext_id)
    created_at: ValueSchemaField = ValueSchemaField(name=ExtraFields.created_at)
    updated_at: ValueSchemaField = ValueSchemaField(name=ExtraFields.updated_at)

    @staticmethod
    def _get_subset_from_subscript(nested_field_keys: Iterable, subscript: List, subscript_type: SubscriptType) -> List:
        if subscript_type == SubscriptType.KEYS:
            sorted_keys = sorted(list(nested_field_keys))
            if len(sorted_keys) < 0:
                return []
            return sorted_keys[subscript[0] : min(subscript[1], len(sorted_keys))]  # noqa E203
        else:
            sorted_keys = sorted(list(nested_field_keys))
            return [sorted_keys[key] for key in subscript] if len(sorted_keys) > 0 else list()

    def _update_hashes(self, value: Union[Dict[str, Any], Any], field: str, hashes: Dict[str, Any]):
        if getattr(self, field).on_write == SchemaFieldWritePolicy.HASH_UPDATE:
            if isinstance(value, dict):
                hashes[field] = {k: sha256(str(v).encode("utf-8")) for k, v in value.items()}
            else:
                hashes[field] = sha256(str(value).encode("utf-8"))

    async def read_context(
        self, fields: _ReadKeys, ctx_reader: _ReadContextFunction, ext_id: str, int_id: str
    ) -> Tuple[Context, Dict]:
        fields_subscript = dict()
        field_props: BaseSchemaField
        for field, field_props in dict(self).items():
            if field_props.on_read == SchemaFieldReadPolicy.IGNORE:
                fields_subscript[field] = False
            elif isinstance(field_props, ListSchemaField):
                list_field_indices = fields.get(field, list())
                update_field = self._get_subset_from_subscript(
                    list_field_indices, field_props.subscript, field_props.subscript_type
                )
                fields_subscript[field] = {field: True for field in update_field}
            elif isinstance(field_props, DictSchemaField):
                update_field = field_props.subscript
                if ALL_ITEMS in update_field:
                    update_field = fields.get(field, list())
                fields_subscript[field] = {field: True for field in update_field}
            else:
                fields_subscript[field] = True

        hashes = dict()
        ctx_dict = await ctx_reader(fields_subscript, int_id, ext_id)
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
            if field_props.on_write == SchemaFieldWritePolicy.IGNORE:
                continue
            elif field_props.on_write == SchemaFieldWritePolicy.UPDATE_ONCE and hashes is not None:
                continue

            elif isinstance(field_props, ListSchemaField):
                list_field_indices = fields.get(field, list())
                update_field = self._get_subset_from_subscript(
                    ctx_dict[field].keys(), field_props.subscript, field_props.subscript_type
                )
                if field_props.on_write == SchemaFieldWritePolicy.APPEND:
                    patch_dict[field] = {
                        idx: ctx_dict[field][idx] for idx in set(update_field) - set(list_field_indices)
                    }
                else:
                    patch_dict[field] = {idx: ctx_dict[field][idx] for idx in update_field}

            elif isinstance(field_props, DictSchemaField):
                dictionary_field_keys = fields.get(field, list())
                update_field = field_props.subscript
                update_keys_all = dictionary_field_keys + list(ctx_dict[field].keys())
                update_keys = set(update_keys_all if ALL_ITEMS in update_field else update_field)

                if field_props.on_write == SchemaFieldWritePolicy.HASH_UPDATE:
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
