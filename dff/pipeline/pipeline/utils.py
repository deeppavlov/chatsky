"""
Utils
-----
The Utils module contains several service functions that are commonly used throughout the framework.
These functions provide a variety of utility functionality.
"""
import collections
from typing import Union, List
from inspect import isfunction

from ..service.service import Service
from ..service.group import ServiceGroup


def pretty_format_component_info_dict(
    service: dict,
    show_extra_handlers: bool,
    offset: str = "",
    extra_handlers_key: str = "extra_handlers",
    type_key: str = "type",
    name_key: str = "name",
    indent: int = 4,
) -> str:
    """
    Function for dumping any pipeline components info dictionary (received from `info_dict` property) as a string.
    Resulting string is formatted with YAML-like format, however it's not strict and shouldn't be parsed.
    However, most preferable usage is via `pipeline.pretty_format`.

    :param service: (required) Pipeline components info dictionary.
    :param show_wrappers: (required) Whether to include Wrappers or not (could be many and/or generated).
    :param offset: Current level new line offset.
    :param wrappers_key: Key that is mapped to Wrappers lists.
    :param type_key: Key that is mapped to components type name.
    :param name_key: Key that is mapped to components name.
    :param indent: Current level new line offset (whitespace number).
    :return: Formatted string
    """
    indent = " " * indent
    representation = f"{offset}{service.get(type_key, '[None]')}%s:\n" % (
        f" '{service.get(name_key, '[None]')}'" if name_key in service else ""
    )
    for key, value in service.items():
        if key not in (type_key, name_key, extra_handlers_key) or (key == extra_handlers_key and show_extra_handlers):
            if isinstance(value, List):
                if len(value) > 0:
                    values = [
                        pretty_format_component_info_dict(instance, show_extra_handlers, f"{indent * 2}{offset}")
                        for instance in value
                    ]
                    value_str = "\n%s" % "\n".join(values)
                else:
                    value_str = "[None]"
            else:
                value_str = str(value)
            representation += f"{offset}{indent}{key}: {value_str}\n"
    return representation[:-1]


def rename_component_incrementing(
    service: Union[Service, ServiceGroup], collisions: List[Union[Service, ServiceGroup]]
) -> str:
    """
    Function for generating new name for a pipeline component,
    that has similar name with other components in the same group.
    The name is generated according to these rules:

    - If service's handler is "ACTOR", it is named `actor`.
    - If service's handler is `Callable`, it is named after this `callable`.
    - If it's a service group, it is named `service_group`.
    - Otherwise, it is names `noname_service`.
    - | After that, `_[NUMBER]` is added to the resulting name,
        where `_[NUMBER]` is number of components with the same name in current service group.

    :param service: Service to be renamed.
    :param collisions: Services in the same service group as service.
    :return: Generated name
    """
    if isinstance(service, Service) and isinstance(service.handler, str) and service.handler == "ACTOR":
        base_name = "actor"
    elif isinstance(service, Service) and callable(service.handler):
        if isfunction(service.handler):
            base_name = service.handler.__name__
        else:
            base_name = service.handler.__class__.__name__
    elif isinstance(service, ServiceGroup):
        base_name = "service_group"
    else:
        base_name = "noname_service"

    name_index = 0
    while f"{base_name}_{name_index}" in [component.name for component in collisions]:
        name_index += 1
    return f"{base_name}_{name_index}"


def finalize_service_group(service_group: ServiceGroup, path: str = ".") -> bool:
    """
    Function that iterates through a service group (and all its subgroups),
    finalizing component's names and paths in it.
    Components are renamed only if user didn't set a name for them. Their paths are also generated here.
    It also searches for "ACTOR" in the group, throwing exception if no actor or multiple actors found.

    :param service_group: Service group to resolve name collisions in.
    :param path:
        A prefix for component paths -- path of `component` is equal to `{path}.{component.name}`.
        Defaults to ".".
    """
    actor = False
    names_counter = collections.Counter([component.name for component in service_group.components])
    for component in service_group.components:
        if component.name is None:
            component.name = rename_component_incrementing(component, service_group.components)
        elif names_counter[component.name] > 1:
            raise Exception(f"User defined service name collision ({path})!")
        component.path = f"{path}.{component.name}"

        if isinstance(component, Service) and isinstance(component.handler, str) and component.handler == "ACTOR":
            actor_found = True
        elif isinstance(component, ServiceGroup):
            actor_found = finalize_service_group(component, f"{path}.{component.name}")
        else:
            actor_found = False

        if actor_found:
            if not actor:
                actor = actor_found
            else:
                raise Exception(f"More than one actor found in group ({path})!")
    return actor
