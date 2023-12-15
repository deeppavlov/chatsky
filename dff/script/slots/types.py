"""
Types
-----
This module encapsulates different types of slots.
"""
import re
from abc import ABC, abstractmethod
from copy import copy
from collections.abc import Iterable
from typing import Callable, Any, Tuple, Dict, Union, Optional

from pydantic import Field, BaseModel, field_validator

from dff.script import Context
from dff.pipeline.pipeline.pipeline import Pipeline, SLOT_STORAGE_KEY
from .utils import singleton


class BaseSlot(BaseModel, ABC, arbitrary_types_allowed=True):
    """
    BaseSlot is a base class for all slots.
    Not meant for direct subclassing, unlike :py:class:`~.ValueSlot` and :py:class:`~._GroupSlot`.
    """

    name: str
    children: Optional[Dict[str, "BaseSlot"]]

    @field_validator("name", mode="before")
    def validate_name(cls, name: str) -> str:
        if "/" in name:
            raise ValueError("Character `/` cannot be used in slot names.")
        return name

    def __init__(self, name: str, **data) -> None:
        super().__init__(name=name, **data)

    def __deepcopy__(self) -> "BaseSlot":
        return copy(self)

    def __eq__(self, other: "BaseSlot") -> bool:
        return self.model_dump(exclude={"name"}) == other.model_dump(exclude={"name"})

    def has_children(self) -> bool:
        return self.children is not None and len(self.children) > 0

    @abstractmethod
    def unset_value(self) -> Callable[[Context, Pipeline], None]:
        raise NotImplementedError("Base class has no attribute 'value'")

    @abstractmethod
    def get_value(self) -> Callable[[Context, Pipeline], Dict[str, Union[str, None]]]:
        raise NotImplementedError("Base class has no attribute 'value'")

    @abstractmethod
    def is_set(self) -> Callable[[Context, Pipeline], bool]:
        raise NotImplementedError("Base class has no attribute 'value'")

    @abstractmethod
    def fill_template(self, template: str) -> Callable[[Context, Pipeline], str]:
        raise NotImplementedError("Base class has no attribute 'value'")

    @abstractmethod
    def extract_value(self, ctx: Context, pipeline: Pipeline) -> Any:
        """
        `Extract value` method is distinct for most slots. So, if you would like to
        introduce your own slot type, it is assumed, that you will override the
        extract_value method.
        """
        raise NotImplementedError("Base class has no attribute 'value'")


class _GroupSlot(BaseSlot):
    """
    Base class for :py:class:`~.RootSlot` and :py:class:`~.GroupSlot`.

    """

    value: None = Field(None)
    children: Dict[str, BaseSlot] = Field(default_factory=dict)

    @field_validator("children", mode="before")
    def validate_children(cls, children: Iterable, values: Dict[str, Any]) -> Dict[str, BaseSlot]:
        if not isinstance(children, dict) and isinstance(children, Iterable):
            children = {child.name: child for child in children}
        if len(children) == 0:
            name = values["name"]
            raise ValueError(f"Error in slot {name}: group slot should have at least one child or more.")
        return children

    def is_set(self) -> Callable[[Context, Pipeline], bool]:
        def is_set_inner(ctx: Context, pipeline: Pipeline) -> bool:
            return all([child.is_set()(ctx, pipeline) for child in self.children.values()])

        return is_set_inner

    def get_value(self) -> Callable[[Context, Pipeline], Dict[str, Union[str, None]]]:
        def get_inner(ctx: Context, pipeline: Pipeline) -> Dict[str, Union[str, None]]:
            values = dict()
            for child in self.children.values():
                if isinstance(child, _GroupSlot):
                    values.update({key: value for key, value in child.get_value()(ctx, pipeline).items()})
                else:
                    values.update({child.name: child.value})
            return values

        return get_inner

    def unset_value(self) -> Callable[[Context, Pipeline], None]:
        def unset_inner(ctx: Context, pipeline: Pipeline) -> None:
            for child in self.children.values():
                child.unset_value()(ctx, pipeline)

        return unset_inner

    def fill_template(self, template: str) -> Callable[[Context, Pipeline], str]:
        def fill_inner(ctx: Context, pipeline: Pipeline) -> str:
            new_template = template
            for _, child in self.children.items():
                new_template = child.fill_template(new_template)(ctx, pipeline)

            return new_template

        return fill_inner

    def extract_value(self, ctx: Context, pipeline: Pipeline) -> Any:
        for child in self.children.values():
            _ = child.extract_value(ctx, pipeline)
        return self.get_value()(ctx, pipeline)


@singleton()
class RootSlot(_GroupSlot):
    """
    Root slot is a universally unique slot group that automatically
    registers all the other slots and makes them globally available.

    """

    @staticmethod
    def flatten_slot_tree(node: BaseSlot) -> Tuple[Dict[str, BaseSlot], Dict[str, BaseSlot]]:
        add_nodes = {node.name: node}
        remove_nodes = {}
        if node.has_children():
            for name, child in node.children.items():
                remove_nodes.update({child.name: child})
                child.name = "/".join([node.name, name])
                child_add_nodes, child_remove_nodes = RootSlot.flatten_slot_tree(child)
                add_nodes.update(child_add_nodes)
                remove_nodes.update(child_remove_nodes)
        return add_nodes, remove_nodes

    def add_slots(self, slots: Union[BaseSlot, Iterable]) -> None:
        if isinstance(slots, BaseSlot):
            add_nodes, _ = self.flatten_slot_tree(slots)
            self.children.update(add_nodes)
        else:
            for slot in slots:
                self.add_slots(slot)


root_slot: RootSlot = RootSlot(name="root")


class ChildSlot(BaseSlot):
    def __init__(self, *, name, **kwargs) -> None:
        super().__init__(name=name, **kwargs)
        root_slot.add_slots(self)


class GroupSlot(_GroupSlot, ChildSlot):
    """
    This class defines a slot group that includes one or more :py:class:`~.ValueSlot` instances.
    When a slot has been included to a group, it should further be referenced as a part of that group.
    E. g. when slot 'name' is included to a group 'person',
    from that point on it should be referenced as 'person/name'.

    """

    ...


class ValueSlot(ChildSlot):
    """
    Value slot is a base class for all slots that are designed to store and extract concrete values.
    Subclass it, if you want to declare your own slot type.

    """

    children: None = Field(None)
    value: Any = None

    def is_set(self) -> Callable[[Context, Pipeline], bool]:
        def is_set_inner(ctx: Context, _: Pipeline) -> bool:
            return bool(ctx.framework_states.get(SLOT_STORAGE_KEY, {}).get(self.name))

        return is_set_inner

    def get_value(self) -> Callable[[Context, Pipeline], Union[str, None]]:
        def get_inner(ctx: Context, _: Pipeline) -> Union[str, None]:
            return ctx.framework_states.get(SLOT_STORAGE_KEY, {}).get(self.name)

        return get_inner

    def unset_value(self) -> Callable[[Context, Pipeline], None]:
        def unset_inner(ctx: Context, _: Pipeline) -> None:
            ctx.framework_states.setdefault(SLOT_STORAGE_KEY, {})
            ctx.framework_states[SLOT_STORAGE_KEY][self.name] = None

        return unset_inner

    def fill_template(self, template: str) -> Callable[[Context, Pipeline], Union[str, None]]:
        """
        Value Slot's `fill_template` method does not perform template filling on its own, but allows you
        to cut corners on some standard operations. E. g., if you include the following snippet in
        the `fill_inner` function, the target slot name is guaranteed to be in the template, while the
        target slot itself is guaranteed to be set.

        .. code-block::

            checked_template = super(RegexpSlot, self).fill_template(template)(ctx, pipeline)
            if not checked_template:
                return '...some stub response...'

        Thus, if you don't want to add any customizations, you can just replace the slot name and return
        the yielded string.

        .. code-block::

            value = ctx.framework_states["slots"][self.name]
            return checked_template.replace("{" + self.name + "}", value)

        Meanwhile, you can choose any other replacement string, depending on the slot value.

        .. code-block::

            value = ctx.framework_states["slots"][self.name]
            new_value = "biggie" if value == "big" else value
            return checked_template.replace("{" + self.name + "}", new_value)

        """

        def fill_inner(ctx: Context, pipeline: Pipeline) -> Union[str, None]:
            if self.name not in template or self.get_value()(ctx, pipeline) is None:
                return None
            return template

        return fill_inner


class RegexpSlot(ValueSlot):
    """
    RegexpSlot is a slot type that extracts its value using a regular expression.
    You can pass a compiled or a non-compiled pattern to the `regexp` argument.
    If you want to extract a particular group, but not the full match,
    change the `target_group` parameter.

    """

    regexp: str
    match_group_idx: int = 0

    def fill_template(self, template: str) -> Callable[[Context, Pipeline], str]:
        def fill_inner(ctx: Context, pipeline: Pipeline) -> str:
            checked_template = super(RegexpSlot, self).fill_template(template)(ctx, pipeline)
            if checked_template is None:  # the check returning None means that an error has occured.
                return template

            value = ctx.framework_states[SLOT_STORAGE_KEY][self.name]
            return checked_template.replace("{" + self.name + "}", value)

        return fill_inner

    def extract_value(self, ctx: Context, _: Pipeline) -> Any:
        search = re.search(self.regexp, ctx.last_request.text)
        self.value = search.group(self.match_group_idx) if search else None
        return self.value


class FunctionSlot(ValueSlot):
    """
    FunctionSlot employs user-defined callables to extract matches from a string.
    The signature of a callable is fixed: it can only get and return strings.

    """

    func: Callable[[str], str]

    def fill_template(self, template: str) -> Callable[[Context, Pipeline], str]:
        def fill_inner(ctx: Context, pipeline: Pipeline) -> str:
            checked_template = super(FunctionSlot, self).fill_template(template)(ctx, pipeline)
            if not checked_template:  # the check returning None means that an error has occured.
                return template

            value = ctx.framework_states[SLOT_STORAGE_KEY][self.name]
            return checked_template.replace("{" + self.name + "}", value)

        return fill_inner

    def extract_value(self, ctx: Context, _: Pipeline) -> Any:
        self.value = self.func(ctx.last_request.text)
        return self.value
