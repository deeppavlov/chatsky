import time
from hashlib import sha256
from enum import Enum
import uuid
from pydantic import BaseModel
from typing import Dict, List, Optional, Tuple, Callable, Any, Union, Awaitable, Hashable
from typing_extensions import Literal

from dff.script import Context

ALL_ITEMS = "__all__"


class SchemaFieldReadPolicy(str, Enum):
    READ = "read"
    IGNORE = "ignore"


class SchemaFieldWritePolicy(str, Enum):
    IGNORE = "ignore"
    UPDATE = "update"
    HASH_UPDATE = "hash_update"
    APPEND = "append"


_ReadContextFunction = Callable[[Dict[str, Union[bool, int, List[Hashable]]], str], Awaitable[Dict]]
_WriteContextFunction = Callable[[str, Union[Dict[str, Any], Any], bool, bool, str], Awaitable]


class BaseSchemaField(BaseModel):
    name: str
    on_read: SchemaFieldReadPolicy = SchemaFieldReadPolicy.READ
    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.IGNORE


class ListSchemaField(BaseSchemaField):
    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.APPEND
    subscript: Union[Literal["__all__"], int] = -1


class DictSchemaField(BaseSchemaField):
    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.HASH_UPDATE
    subscript: Union[Literal["__all__"], List[Hashable]] = ALL_ITEMS


class ValueSchemaField(BaseSchemaField):
    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.UPDATE


class ExtraFields(str, Enum):
    primary_id = "primary_id"
    storage_key = "storage_key"
    active_ctx = "active_ctx"
    created_at = "created_at"
    updated_at = "updated_at"


class ContextSchema(BaseModel):
    active_ctx: ValueSchemaField = ValueSchemaField(name=ExtraFields.active_ctx)
    storage_key: ValueSchemaField = ValueSchemaField(name=ExtraFields.storage_key)
    requests: ListSchemaField = ListSchemaField(name="requests")
    responses: ListSchemaField = ListSchemaField(name="responses")
    labels: ListSchemaField = ListSchemaField(name="labels")
    misc: DictSchemaField = DictSchemaField(name="misc")
    framework_states: DictSchemaField = DictSchemaField(name="framework_states")
    created_at: ValueSchemaField = ValueSchemaField(name=ExtraFields.created_at)
    updated_at: ValueSchemaField = ValueSchemaField(name=ExtraFields.updated_at)

    def _calculate_hashes(self, value: Union[Dict[str, Any], Any]) -> Union[Dict[str, Any], Hashable]:
        if isinstance(value, dict):
            return {k: sha256(str(v).encode("utf-8")) for k, v in value.items()}
        else:
            return sha256(str(value).encode("utf-8"))

    async def read_context(self, ctx_reader: _ReadContextFunction, primary_id: str) -> Tuple[Context, Dict]:
        fields_subscript = dict()
        field_props: BaseSchemaField

        for field, field_props in dict(self).items():
            if field_props.on_read == SchemaFieldReadPolicy.IGNORE:
                fields_subscript[field] = False
            elif isinstance(field_props, ListSchemaField) or isinstance(field_props, DictSchemaField):
                fields_subscript[field] = field_props.subscript
            else:
                fields_subscript[field] = True

        hashes = dict()
        ctx_dict = await ctx_reader(fields_subscript, primary_id)
        for key in ctx_dict.keys():
            hashes[key] = self._calculate_hashes(ctx_dict[key])

        return Context.cast(ctx_dict), hashes

    async def write_context(
        self, ctx: Context, hashes: Optional[Dict], val_writer: _WriteContextFunction, storage_key: str, primary_id: Optional[str]
    ):
        ctx.storage_key = storage_key
        ctx_dict = ctx.dict()
        primary_id = str(uuid.uuid4()) if primary_id is None else primary_id

        ctx_dict[self.active_ctx.name] = True
        ctx_dict[self.created_at.name] = ctx_dict[self.updated_at.name] = time.time_ns()

        field_props: BaseSchemaField
        for field, field_props in dict(self).items():
            update_values = ctx_dict[field]
            update_nested = not isinstance(field_props, ValueSchemaField)
            if field_props.on_write == SchemaFieldWritePolicy.IGNORE:
                continue
            elif field_props.on_write == SchemaFieldWritePolicy.HASH_UPDATE:
                update_enforce = True
                if hashes is not None and hashes.get(field) is not None:
                    new_hashes = self._calculate_hashes(ctx_dict[field])
                    if isinstance(new_hashes, dict):
                        update_values = {k: v for k, v in ctx_dict[field].items() if hashes[field][k] != new_hashes[k]}
                    else:
                        update_values = ctx_dict[field] if hashes[field] != new_hashes else False
            elif field_props.on_write == SchemaFieldWritePolicy.APPEND:
                update_enforce = False
            else:
                update_enforce = True
            await val_writer(field, update_values, update_enforce, update_nested, primary_id)
