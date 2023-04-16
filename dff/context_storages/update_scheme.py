import time
from hashlib import sha256
from re import compile
from enum import Enum, auto, unique
from typing import Dict, List, Optional, Tuple, Iterable, Callable, Any, Union, Awaitable, Hashable

from dff.script import Context


@unique
class FieldType(Enum):
    LIST = auto()
    DICT = auto()
    VALUE = auto()


_ReadKeys = Dict[str, List[str]]
_ReadContextFunction = Callable[[Dict[str, Union[bool, Dict[Hashable, bool]]], str, str], Awaitable[Dict]]
_WriteContextFunction = Callable[[Dict[str, Any], str, str], Awaitable]


@unique
class FieldRule(Enum):
    READ = auto()
    IGNORE = auto()
    UPDATE = auto()
    HASH_UPDATE = auto()
    UPDATE_ONCE = auto()
    APPEND = auto()


UpdateSchemeBuilder = Dict[str, Union[Tuple[str], Tuple[str, str]]]


class ExtraFields:
    IDENTITY_FIELD = "id"
    EXTERNAL_FIELD = "ext_id"
    CREATED_AT_FIELD = "created_at"
    UPDATED_AT_FIELD = "updated_at"


# TODO: extend from pydantic.BaseModel + validators.
class UpdateScheme:
    ALL_ITEMS = "__all__"

    EXTRA_FIELDS = [v for k, v in ExtraFields.__dict__.items() if not (k.startswith("__") and k.endswith("__"))]
    ALL_FIELDS = set(EXTRA_FIELDS + list(Context.__fields__.keys()))

    _FIELD_NAME_PATTERN = compile(r"^(.+?)(\[.+\])?$")
    _LIST_FIELD_NAME_PATTERN = compile(r"^.+?(\[([^\[\]]+)\])$")
    _DICT_FIELD_NAME_PATTERN = compile(r"^.+?\[(\[.+\])\]$")

    def __init__(self, dict_scheme: UpdateSchemeBuilder):
        self.fields = dict()
        for name, rules in dict_scheme.items():
            field_type = self._get_type_from_name(name)
            if field_type is None:
                raise Exception(f"Field '{name}' not supported by update scheme!")
            field, field_name = self._init_update_field(field_type, name, list(rules))
            self.fields[field_name] = field
        for name in list(self.ALL_FIELDS - self.fields.keys()):
            self.fields[name] = self._init_update_field(self._get_type_from_name(name), name, ["ignore", "ignore"])[0]

    @classmethod
    def _get_type_from_name(cls, field_name: str) -> Optional[FieldType]:
        if field_name.startswith("requests") or field_name.startswith("responses") or field_name.startswith("labels"):
            return FieldType.LIST
        elif field_name.startswith("misc") or field_name.startswith("framework_states"):
            return FieldType.DICT
        else:
            return FieldType.VALUE

    @classmethod
    def _init_update_field(cls, field_type: FieldType, field_name: str, rules: List[str]) -> Tuple[Dict, str]:
        field = {"type": field_type}

        if len(rules) == 0:
            raise Exception(f"For field '{field_name}' the read rule should be defined!")
        elif len(rules) > 2:
            raise Exception(f"For field '{field_name}' more then two (read, write) rules are defined!")
        elif len(rules) == 1:
            rules.append("ignore")

        if rules[0] == "ignore":
            read_rule = FieldRule.IGNORE
        elif rules[0] == "read":
            read_rule = FieldRule.READ
        else:
            raise Exception(f"For field '{field_name}' unknown read rule: '{rules[0]}'!")
        field["read"] = read_rule

        if rules[1] == "ignore":
            write_rule = FieldRule.IGNORE
        elif rules[1] == "update":
            write_rule = FieldRule.UPDATE
        elif rules[1] == "hash_update":
            write_rule = FieldRule.HASH_UPDATE
        elif rules[1] == "update_once":
            write_rule = FieldRule.UPDATE_ONCE
        elif rules[1] == "append":
            write_rule = FieldRule.APPEND
        else:
            raise Exception(f"For field '{field_name}' unknown write rule: '{rules[1]}'!")
        field["write"] = write_rule

        list_write_wrong_rule = field_type == FieldType.LIST and (write_rule == FieldRule.UPDATE or write_rule == FieldRule.HASH_UPDATE)
        field_write_wrong_rule = field_type != FieldType.LIST and write_rule == FieldRule.APPEND
        if list_write_wrong_rule or field_write_wrong_rule:
            raise Exception(f"Write rule '{write_rule}' not defined for field '{field_name}' of type '{field_type}'!")

        split = cls._FIELD_NAME_PATTERN.match(field_name)
        if field_type == FieldType.VALUE:
            if split.group(2) is not None:
                raise Exception(f"Field '{field_name}' shouldn't have an outlook value - it is of type '{field_type}'!")
            field_name_pure = field_name
        else:
            if split.group(2) is None:
                field_name += "[:]" if field_type == FieldType.LIST else "[[:]]"
            field_name_pure = split.group(1)

        if field_type == FieldType.LIST:
            outlook_match = cls._LIST_FIELD_NAME_PATTERN.match(field_name)
            if outlook_match is None:
                raise Exception(f"Outlook for field '{field_name}' isn't formatted correctly!")

            outlook = outlook_match.group(2).split(":")
            if len(outlook) == 1:
                if outlook == "":
                    raise Exception(f"Outlook array empty for field '{field_name}'!")
                else:
                    try:
                        outlook = eval(outlook_match.group(1), {}, {})
                    except Exception as e:
                        raise Exception(f"While parsing outlook of field '{field_name}' exception happened: {e}")
                    if not isinstance(outlook, List):
                        raise Exception(f"Outlook of field '{field_name}' exception isn't a list - it is of type '{field_type}'!")
                    if not all([isinstance(item, int) for item in outlook]):
                        raise Exception(f"Outlook of field '{field_name}' contains non-integer values!")
                    field["outlook_list"] = outlook
            else:
                if len(outlook) > 3:
                    raise Exception(f"Outlook for field '{field_name}' isn't formatted correctly: '{outlook_match.group(2)}'!")
                elif len(outlook) == 2:
                    outlook.append("1")

                if outlook[0] == "":
                    outlook[0] = "0"
                if outlook[1] == "":
                    outlook[1] = "-1"
                if outlook[2] == "":
                    outlook[2] = "1"
                field["outlook_slice"] = [int(index) for index in outlook]

        elif field_type == FieldType.DICT:
            outlook_match = cls._DICT_FIELD_NAME_PATTERN.match(field_name)
            if outlook_match is None:
                raise Exception(f"Outlook for field '{field_name}' isn't formatted correctly!")

            try:
                outlook = eval(outlook_match.group(1), {}, {"all": cls.ALL_ITEMS})
            except Exception as e:
                raise Exception(f"While parsing outlook of field '{field_name}' exception happened: {e}")
            if not isinstance(outlook, List):
                raise Exception(f"Outlook of field '{field_name}' exception isn't a list - it is of type '{field_type}'!")
            if cls.ALL_ITEMS in outlook and len(outlook) > 1:
                raise Exception(f"Element 'all' should be the only element of the outlook of the field '{field_name}'!")
            field["outlook"] = outlook

        return field, field_name_pure

    def mark_db_not_persistent(self):
        for field, rules in self.fields.items():
            if rules["write"] in (FieldRule.HASH_UPDATE, FieldRule.UPDATE_ONCE, FieldRule.APPEND):
                rules["write"] = FieldRule.UPDATE

    @staticmethod
    def _get_outlook_slice(dictionary_keys: Iterable, update_field: List) -> List:
        list_keys = sorted(list(dictionary_keys))
        update_field[1] = min(update_field[1], len(list_keys))
        return list_keys[update_field[0]:update_field[1]:update_field[2]] if len(list_keys) > 0 else list()

    @staticmethod
    def _get_outlook_list(dictionary_keys: Iterable, update_field: List) -> List:
        list_keys = sorted(list(dictionary_keys))
        return [list_keys[key] for key in update_field] if len(list_keys) > 0 else list()

    def _update_hashes(self, value: Union[Dict[str, Any], Any], field: str, hashes: Dict[str, Any]):
        if self.fields[field]["write"] == FieldRule.HASH_UPDATE:
            if isinstance(value, dict):
                hashes[field] = {k: sha256(str(v).encode("utf-8")) for k, v in value.items()}
            else:
                hashes[field] = sha256(str(value).encode("utf-8"))

    async def read_context(self, fields: _ReadKeys, ctx_reader: _ReadContextFunction, ext_id: str, int_id: str) -> Tuple[Context, Dict]:
        fields_outlook = dict()
        for field in self.fields.keys():
            if self.fields[field]["read"] == FieldRule.IGNORE:
                fields_outlook[field] = False
            elif self.fields[field]["type"] == FieldType.LIST:
                list_keys = fields.get(field, list())
                if "outlook_slice" in self.fields[field]:
                    update_field = self._get_outlook_slice(list_keys, self.fields[field]["outlook_slice"])
                else:
                    update_field = self._get_outlook_list(list_keys, self.fields[field]["outlook_list"])
                fields_outlook[field] = {field: True for field in update_field}
            elif self.fields[field]["type"] == FieldType.DICT:
                update_field = self.fields[field].get("outlook", None)
                if self.ALL_ITEMS in update_field:
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

    async def write_context(self, ctx: Context, hashes: Optional[Dict], fields: _ReadKeys, val_writer: _WriteContextFunction, ext_id: str):
        ctx_dict = ctx.dict()
        ctx_dict[ExtraFields.EXTERNAL_FIELD] = str(ext_id)
        ctx_dict[ExtraFields.CREATED_AT_FIELD] = ctx_dict[ExtraFields.UPDATED_AT_FIELD] = time.time_ns()

        patch_dict = dict()
        for field in self.fields.keys():
            if self.fields[field]["write"] == FieldRule.IGNORE:
                continue
            elif self.fields[field]["write"] == FieldRule.UPDATE_ONCE and hashes is not None:
                continue
            elif self.fields[field]["type"] == FieldType.LIST:
                list_keys = fields.get(field, list())
                if "outlook_slice" in self.fields[field]:
                    update_field = self._get_outlook_slice(ctx_dict[field].keys(), self.fields[field]["outlook_slice"])
                else:
                    update_field = self._get_outlook_list(ctx_dict[field].keys(), self.fields[field]["outlook_list"])
                if self.fields[field]["write"] == FieldRule.APPEND:
                    patch_dict[field] = {item: ctx_dict[field][item] for item in set(update_field) - set(list_keys)}
                elif self.fields[field]["write"] == FieldRule.HASH_UPDATE:
                    patch_dict[field] = dict()
                    for item in update_field:
                        item_hash = sha256(str(ctx_dict[field][item]).encode("utf-8"))
                        if hashes is None or hashes.get(field, dict()).get(item, None) != item_hash:
                            patch_dict[field][item] = ctx_dict[field][item]
                else:
                    patch_dict[field] = {item: ctx_dict[field][item] for item in update_field}
            elif self.fields[field]["type"] == FieldType.DICT:
                list_keys = fields.get(field, list())
                update_field = self.fields[field].get("outlook", list())
                update_keys_all = list_keys + list(ctx_dict[field].keys())
                update_keys = set(update_keys_all if self.ALL_ITEMS in update_field else update_field)
                if self.fields[field]["write"] == FieldRule.APPEND:
                    patch_dict[field] = {item: ctx_dict[field][item] for item in update_keys - set(list_keys)}
                elif self.fields[field]["write"] == FieldRule.HASH_UPDATE:
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


default_update_scheme = {
    "id": ("read",),
    "requests[-1]": ("read", "append"),
    "responses[-1]": ("read", "append"),
    "labels[-1]": ("read", "append"),
    "misc[[all]]": ("read", "hash_update"),
    "framework_states[[all]]": ("read", "hash_update"),
}

full_update_scheme = {
    "id": ("read",),
    "requests[:]": ("read", "append"),
    "responses[:]": ("read", "append"),
    "labels[:]": ("read", "append"),
    "misc[[all]]": ("read", "update"),
    "framework_states[[all]]": ("read", "update"),
}
