"""
Utils
-----
The Utils module contains functions used to provide names to nameless pipeline components inside of a group.
"""

import collections
from typing import List

from chatsky.core import Context
from chatsky.core.context import ServiceState
from .service.component import PipelineComponent
from .service.group import ServiceGroup


def rename_component_incrementing(index: int, computed_names: List[str]) -> str:
    """
    Function for generating new name for a pipeline component,
    that has similar name with other components in the same group.

    The name is generated according to these rules:

    1. Base name is :py:attr:`.PipelineComponent.computed_name`;
    2. If there are multiple components with the same name, ``#[NUMBER]`` is added to the resulting name,
       where ``NUMBER`` is the number of components with the same name in current service group.

    :param index: Index of the component to be renamed.
    :param computed_names: A list of component names (or computed names).
    :return: Name for the component.
    """
    base_name = computed_names[index]
    if computed_names.count(base_name) == 1:
        return base_name
    else:
        return f"{base_name}#{computed_names[:index].count(base_name)}"


def finalize_service_group(service_group: ServiceGroup, path: str = "") -> None:
    """
    Function that iterates through a service group (and all its subgroups),
    finalizing component's names and paths in it.
    Components are renamed only if user didn't set a name for them. Their paths are also generated here.

    :param service_group: Service group to resolve name collisions in.
    :param path:
        A prefix for component paths -- path of `component` is equal to `{path}.{component.name}`.
        Defaults to "".
    :raises ValueError: If multiple components have the same name assigned to them.
    """
    computed_names = [
        component.name if component.name is not None else component.computed_name
        for component in service_group.components
    ]
    for idx, component in enumerate(service_group.components):
        if component.name is None:
            component.name = rename_component_incrementing(idx, computed_names)
        component.path = f"{path}.{component.name}"

    new_names_counter = collections.Counter([component.name for component in service_group.components])
    for k, v in new_names_counter.items():
        if v != 1:
            raise ValueError("Found multiple components with the same name: {path}.{k}")

    for component in service_group.components:
        if isinstance(component, ServiceGroup):
            finalize_service_group(component, f"{path}.{component.name}")


def initialize_service_states(ctx: Context, service: PipelineComponent) -> None:
    """
    Reset :py:class:`.ServiceState` of `service`.

    Called at the beginning of every turn for the pipeline service group.
    """
    ctx.framework_data.service_states[service.path] = ServiceState()
    if isinstance(service, ServiceGroup):
        for component in service.components:
            initialize_service_states(ctx, component)
