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


def rename_component_incrementing(component: PipelineComponent, collisions: List[PipelineComponent]) -> str:
    """
    Function for generating new name for a pipeline component,
    that has similar name with other components in the same group.

    The name is generated according to these rules:

    1. Base name is :py:attr:`.PipelineComponent.computed_name`;
    2. After that, ``_[NUMBER]`` is added to the resulting name,
       where ``_[NUMBER]`` is number of components with the same name in current service group.

    :param component: Component to be renamed.
    :param collisions: Components in the same service group as component.
    :return: Generated name
    """
    base_name = component.computed_name
    name_index = 0
    while f"{base_name}_{name_index}" in [component.name for component in collisions]:
        name_index += 1
    return f"{base_name}_{name_index}"


def finalize_service_group(service_group: ServiceGroup, path: str = ".") -> None:
    """
    Function that iterates through a service group (and all its subgroups),
    finalizing component's names and paths in it.
    Components are renamed only if user didn't set a name for them. Their paths are also generated here.

    :param service_group: Service group to resolve name collisions in.
    :param path:
        A prefix for component paths -- path of `component` is equal to `{path}.{component.name}`.
        Defaults to ".".
    """
    names_counter = collections.Counter([component.name for component in service_group.components])
    for component in service_group.components:
        if component.name is None:
            component.name = rename_component_incrementing(component, service_group.components)
        elif names_counter[component.name] > 1:
            raise Exception(f"User defined service name collision ({path})!")
        component.path = f"{path}.{component.name}"

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
