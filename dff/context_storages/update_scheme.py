from hashlib import sha256
from re import compile
from enum import Enum, auto, unique
from typing import Dict, List, Optional, Tuple

from dff.script import Context


@unique
class FieldType(Enum):
    LIST = auto()
    DICT = auto()
    VALUE = auto()


@unique
class FieldRule(Enum):
    READ = auto()
    DEFAULT_VALUE = auto()
    IGNORE = auto()
    UPDATE = auto()
    HASH_UPDATE = auto()
    APPEND = auto()


class UpdateScheme:
    _ALL_ITEMS = "__all__"
    _FIELD_NAME_PATTERN = compile(r"^(.+?)(\[.+\])?$")
    _LIST_FIELD_NAME_PATTERN = compile(r"^.+?(\[([^\[\]]+)\])$")
    _DICT_FIELD_NAME_PATTERN = compile(r"^.+?\[(\[.+\])\]$")
    _DEFAULT_VALUE_RULE_PATTERN = compile(r"^default_value\((.+)\)$")

    def __init__(self, dict_scheme: Dict[str, List[str]]):
        self.fields = dict()
        for name, rules in dict_scheme.items():
            field_type = self._get_type_from_name(name)
            if field_type is None:
                raise Exception(f"Field '{name}' not included in Context!")
            field, field_name = self._init_update_field(field_type, name, rules)
            self.fields[field_name] = field

    @classmethod
    def _get_type_from_name(cls, field_name: str) -> Optional[FieldType]:
        if field_name.startswith("requests") or field_name.startswith("responses") or field_name.startswith("labels"):
            return FieldType.LIST
        elif field_name.startswith("misc") or field_name.startswith("framework_states"):
            return FieldType.DICT
        elif field_name.startswith("validation") or field_name.startswith("id"):
            return FieldType.VALUE
        else:
            return None

    @classmethod
    def _init_update_field(cls, field_type: FieldType, field_name: str, rules: List[str]) -> Tuple[Dict, str]:
        field = dict()

        if len(rules) == 0:
            raise Exception(f"For field '{field_name}' the read rule should be defined!")
        elif len(rules) > 2:
            raise Exception(f"For field '{field_name}' more then two (read, write) rules are defined!")
        elif len(rules) == 1:
            rules.append("ignore")

        read_value = None
        if rules[0] == "read":
            read_rule = FieldRule.READ
        elif rules[0].startswith("default_value"):
            read_value = cls._DEFAULT_VALUE_RULE_PATTERN.match(rules[0]).group(1)
            read_rule = FieldRule.DEFAULT_VALUE
        else:
            raise Exception(f"For field '{field_name}' unknown read rule: '{rules[0]}'!")
        field["read"] = read_rule

        if rules[1] == "ignore":
            write_rule = FieldRule.IGNORE
        elif rules[1] == "update":
            write_rule = FieldRule.UPDATE
        elif rules[1] == "hash_update":
            write_rule = FieldRule.HASH_UPDATE
        elif rules[1] == "append":
            write_rule = FieldRule.APPEND
        else:
            raise Exception(f"For field '{field_name}' unknown write rule: '{rules[1]}'!")
        field["write"] = write_rule

        list_write_wrong_rule = field_type == FieldType.LIST and (write_rule == FieldRule.UPDATE or write_rule == FieldRule.HASH_UPDATE)
        field_write_wrong_rule = field_type != FieldType.LIST and write_rule == FieldRule.APPEND
        if list_write_wrong_rule or field_write_wrong_rule:
            raise Exception(f"Write rule '{write_rule}' not defined for field '{field_name}' of type '{field_type}'!")

        if read_rule == FieldRule.DEFAULT_VALUE:
            try:
                read_value = eval(read_value, {}, {})
            except Exception as e:
                raise Exception(f"While parsing default value of field '{field_name}' exception happened: {e}")
            default_list_wrong = field_type == FieldType.LIST and not isinstance(read_value, List)
            default_dict_wrong = field_type == FieldType.DICT and not isinstance(read_value, Dict)
            if default_list_wrong or default_dict_wrong:
                raise Exception(f"Wrong type of default value for field '{field_name}': {type(read_value)}")
            field["value"] = read_value

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
                    field["outlook"] = outlook
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
                field["outlook"] = [int(index) for index in outlook]

        elif field_type == FieldType.DICT:
            outlook_match = cls._DICT_FIELD_NAME_PATTERN.match(field_name)
            if outlook_match is None:
                raise Exception(f"Outlook for field '{field_name}' isn't formatted correctly!")

            try:
                outlook = eval(outlook_match.group(1), {}, {"all": cls._ALL_ITEMS})
            except Exception as e:
                raise Exception(f"While parsing outlook of field '{field_name}' exception happened: {e}")
            if not isinstance(outlook, List):
                raise Exception(f"Outlook of field '{field_name}' exception isn't a list - it is of type '{field_type}'!")
            if cls._ALL_ITEMS in outlook and len(outlook) > 1:
                raise Exception(f"Element 'all' should be the only element of the outlook of the field '{field_name}'!")
            field["outlook"] = outlook

        return field, field_name_pure

    def process_context_read(self, initial: Dict) -> Tuple[Dict, Dict]:
        context_dict = initial.copy()
        context_hash = dict()
        print(self.fields.keys())
        for field in self.fields.keys():
            if self.fields[field]["read"] == FieldRule.DEFAULT_VALUE:
                context_dict[field] = self.fields[field]["value"]
            field_type = self._get_type_from_name(field)
            update_field = self.fields[field].get("outlook", None)
            if field_type is FieldType.LIST:
                list_keys = sorted(list(context_dict[field].keys()))
                list_outlook = list_keys[update_field[0]:update_field[1]:update_field[2]] if len(list_keys) > 0 else list()
                context_dict[field] = {item: context_dict[field][item] for item in list_outlook}
            elif field_type is FieldType.DICT and self._ALL_ITEMS not in update_field:
                context_dict[field] = {item: context_dict[field][item] for item in update_field}
            context_hash[field] = sha256(str(context_dict[field]).encode("utf-8"))
        return context_dict, context_hash

    def process_context_write(self, initial: Dict, ctx: Context) -> Dict:
        context_dict = ctx.dict()
        output_dict = dict()
        for field in self.fields.keys():
            if self.fields[field]["write"] == FieldRule.IGNORE:
                output_dict[field] = initial[field]
                continue
            field_type = self._get_type_from_name(field)
            update_field = self.fields[field].get("outlook", None)
            if field_type is FieldType.LIST:
                list_keys = sorted(list(initial[field].keys()))
                list_outlook = list_keys[update_field[0]:update_field[1]:update_field[2]] if len(list_keys) > 0 else list()
                output_dict[field] = {item: initial[field][item] for item in list_outlook}
                output_dict[field] = {item: context_dict[field][item] for item in list_outlook}
            elif field_type is FieldType.DICT:
                if self._ALL_ITEMS not in update_field:
                    output_dict[field] = {item: initial[field][item] for item in update_field}
                    output_dict[field] = {item: context_dict[field][item] for item in update_field}
                else:
                    output_dict[field] = {item: initial[field][item] for item in initial[field].keys()}
                    output_dict[field] = {item: context_dict[field][item] for item in context_dict[field].keys()}
            else:
                output_dict[field] = context_dict[field]
        return output_dict

    def process_context_create(self) -> Dict:
        pass


default_update_scheme = UpdateScheme({
    "id": ["read"],
    "requests[-1]": ["read", "append"],
    "responses[-1]": ["read", "append"],
    "labels[-1]": ["read", "append"],
    "misc[[all]]": ["read", "hash_update"],
    "framework_states[[all]]": ["read", "hash_update"],
    "validation": ["default_value(False)"],
})

full_update_scheme = UpdateScheme({
    "id": ["read", "update"],
    "requests[:]": ["read", "append"],
    "responses[:]": ["read", "append"],
    "labels[:]": ["read", "append"],
    "misc[[all]]": ["read", "update"],
    "framework_states[[all]]": ["read", "update"],
    "validation": ["read", "update"],
})
