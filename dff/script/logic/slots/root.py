"""
Root
---------------------------
This module contains the root slot and the corresponding type. 
This instance is a singleton, so it will be shared each time you use the add-on.
"""
import wrapt
from typing import Tuple, Dict, overload, Iterable
from functools import singledispatch

from .types import BaseSlot, GroupSlot


def singleton(cls: type):
    def singleton_inner(*args, **kwargs):
        if singleton_inner.instance is None:
            singleton_inner.instance = cls(*args, **kwargs)
        return singleton_inner.instance

    singleton_inner.instance = None
    return singleton_inner


def flatten_slot_tree(node: BaseSlot) -> Tuple[Dict[str, BaseSlot], Dict[str, BaseSlot]]:
    add_nodes = {node.name: node}
    remove_nodes = {}
    if node.has_children():
        for name, child in node.children.items():
            remove_nodes.update({child.name: child})
            child.name = "/".join([node.name, name])
            child_add_nodes, child_remove_nodes = flatten_slot_tree(child)
            add_nodes.update(child_add_nodes)
            remove_nodes.update(child_remove_nodes)
    return add_nodes, remove_nodes


@singleton
class RootSlot(GroupSlot):
    pass


root_slot = RootSlot(name="root_slot")


@overload
def add_slots(slots: BaseSlot) -> None:
    ...


@overload
def add_slots(slots: Iterable[BaseSlot]) -> None:
    ...


def add_slots(slots):
    if isinstance(slots, BaseSlot):
        add_nodes, _ = flatten_slot_tree(slots)
        root_slot.children.update(add_nodes)
    else:
        for slot in slots:
            add_slots(slot)


@wrapt.decorator
def auto_register(cls, _, args, kwargs):
    slot_instance = cls(*args, **kwargs)
    add_slots(slot_instance)
    return slot_instance
