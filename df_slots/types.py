"""
Types
---------------------------
This module encapsulates different types of slots.
Generally, these types should be imported from __init__.py for the sake of automatic registry.
Import from here, if you want to registed slots manually.
"""
import re
from abc import ABC, abstractmethod
import logging
from copy import copy
from collections.abc import Iterable
from typing import Callable, Any, Dict, Union

from df_engine.core import Context, Actor

from pydantic import Field, BaseModel, validator
from pydantic.typing import ForwardRef

from .utils import requires_storage, SLOT_STORAGE_KEY

logger = logging.getLogger(__name__)

BaseSlot = ForwardRef("BaseSlot")


class BaseSlot(BaseModel, ABC):
    """
    BaseSlot is a base class for all slots.
    Not meant for direct subclassing, unlike :py:class:`~ValueSlot` and :py:class:`~GroupSlot`.
    """

    name: str

    @validator("name", pre=True)
    def validate_name(cls, name: str):
        if "/" in name:
            raise ValueError("separator `/` cannot be used in slot names")
        return name

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, name: str, **data):
        super().__init__(name=name, **data)

    def __deepcopy__(self, *args, **kwargs):
        return copy(self)

    def __eq__(self, other: BaseSlot):
        return self.dict(exclude={"name"}) == other.dict(exclude={"name"})

    def has_children(self) -> bool:
        return hasattr(self, "children") and len(self.children) > 0

    @abstractmethod
    def unset_value(self) -> Callable[[Context, Actor], None]:
        raise NotImplementedError("Base class has no attribute 'value'")

    @abstractmethod
    def get_value(self) -> Callable[[Context, Actor], Dict[str, Union[str, None]]]:
        raise NotImplementedError("Base class has no attribute 'value'")

    @abstractmethod
    def is_set(self) -> Callable[[Context, Actor], bool]:
        raise NotImplementedError("Base class has no attribute 'value'")

    @abstractmethod
    def fill_template(self, template: str) -> Callable[[Context, Actor], str]:
        raise NotImplementedError("Base class has no attribute 'value'")

    @abstractmethod
    def extract_value(self, ctx: Context, actor: Actor) -> Any:
        """
        `Extract value` method is distinct for most slots. So, if you would like to
        introduce your own slot type, it is assumed, that you will override the
        extract_value method.
        """
        raise NotImplementedError("Base class has no attribute 'value'")


class GroupSlot(BaseSlot):
    """
    This class defines a slot group that includes one or more :py:class:`~ValueSlot` instances.
    When a slot has been included to a group, it should further be referenced as a part of that group.
    E. g. when slot 'name' is included to a group 'person',
    from that point on it should be referenced as 'person/name'.

    """

    children: Dict[str, BaseSlot] = Field(default_factory=dict)

    @validator("children", pre=True)
    def validate_children(cls, children, values: dict):
        if not isinstance(children, dict) and isinstance(children, Iterable):
            children = {child.name: child for child in children}
        if len(children) == 0:
            name = values["name"]
            raise ValueError(f"Error in slot {name}: group slot should have at least one child or more.")
        return children

    @property
    def value(self):
        values = dict()
        for name, child in self.children.items():
            if isinstance(child, GroupSlot):
                values.update({key: value for key, value in child.value.items()})
            else:
                values.update({child.name: child.value})
        return values

    def is_set(self):
        @requires_storage(f"Can't check value for {self.name}: slot storage missing", return_val=False)
        def is_set_inner(ctx: Context, actor: Actor):
            return all([child.is_set()(ctx, actor) for child in self.children.values()])

        return is_set_inner

    def get_value(self) -> Callable[[Context, Actor], Dict[str, Union[str, None]]]:
        @requires_storage(f"Can't get value for {self.name}: slot storage missing")
        def get_inner(ctx: Context, actor: Actor) -> Dict[str, Union[str, None]]:
            values = dict()
            for child in self.children.values():
                if isinstance(child, GroupSlot):
                    values.update({key: value for key, value in child.get_value()(ctx, actor).items()})
                else:
                    values.update({child.name: child.get_value()(ctx, actor)})
            return values

        return get_inner

    def unset_value(self):
        @requires_storage(f"Can't unset value for {self.name}: slot storage missing")
        def unset_inner(ctx: Context, actor: Actor):
            for child in self.children.values():
                child.unset_value()(ctx, actor)

        return unset_inner

    def fill_template(self, template: str) -> Callable:
        @requires_storage(f"Can't fill a template with {self.name}: slot storage missing.", return_val=template)
        def fill_inner(ctx: Context, actor: Actor) -> str:
            new_template = template
            for _, child in self.children.items():
                new_template = child.fill_template(new_template)(ctx, actor)

            return new_template

        return fill_inner

    def extract_value(self, ctx: Context, actor: Actor):
        for child in self.children.values():
            val = child.extract_value(ctx, actor)
        return self.value


class ValueSlot(BaseSlot):
    """
    Value slot is a base class for all slots that are designed to store and extract concrete values.
    Subclass it, if you want to declare your own slot type.

    """

    value: Any = None

    def is_set(self):
        @requires_storage(f"Can't check value for {self.name}: slot storage missing", return_val=False)
        def is_set_inner(ctx: Context, actor: Actor):
            return bool(ctx.framework_states[SLOT_STORAGE_KEY].get(self.name))

        return is_set_inner

    def get_value(self) -> Callable[[Context, Actor], Union[str, None]]:
        @requires_storage(f"Can't get value for {self.name}: slot storage missing")
        def get_inner(ctx: Context, actor: Actor) -> Union[str, None]:
            return ctx.framework_states[SLOT_STORAGE_KEY].get(self.name)

        return get_inner

    def unset_value(self):
        @requires_storage(f"Can't unset value for {self.name}: slot storage missing")
        def unset_inner(ctx: Context, actor: Actor):
            ctx.framework_states[SLOT_STORAGE_KEY][self.name] = None

        return unset_inner

    def fill_template(self, template: str) -> Callable[[Context, Actor], str]:
        """
        Value Slot's `fill_template` method does not perform template filling on its own, but allows you
        to cut corners on some standard operations. E. g., if you include the following snippet in
        the `fill_inner` function, the target slot name is guaranteed to be in the template, while the
        target slot itself is guaranteed to be set.

        .. code-block::

            checked_template = super(RegexpSlot, self).fill_template(template)(ctx, actor)
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

        @requires_storage(f"Can't fill a template with {self.name}: slot storage missing.")
        def fill_inner(ctx: Context, actor: Actor) -> Union[str, None]:
            if not self.name in template or self.get_value()(ctx, actor) is None:
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

    def fill_template(self, template: str) -> Callable:
        def fill_inner(ctx: Context, actor: Actor):
            checked_template = super(RegexpSlot, self).fill_template(template)(ctx, actor)
            if checked_template is None:  # the check returning None means that an error has occured.
                return template

            value = ctx.framework_states[SLOT_STORAGE_KEY][self.name]
            return checked_template.replace("{" + self.name + "}", value)

        return fill_inner

    def extract_value(self, ctx: Context, actor: Actor):
        search = re.search(self.regexp, ctx.last_request)
        self.value = search.group(self.match_group_idx) if search else None
        return self.value


class FunctionSlot(ValueSlot):
    """
    FunctionSlot employs user-defined callables to extract matches from a string.
    The signature of a callable is fixed: it can only get and return strings.

    """

    func: Callable[[str], str]

    def fill_template(self, template: str) -> Callable:
        def fill_inner(ctx: Context, actor: Actor):
            checked_template = super(FunctionSlot, self).fill_template(template)(ctx, actor)
            if not checked_template:  # the check returning None means that an error has occured.
                return template

            value = ctx.framework_states[SLOT_STORAGE_KEY][self.name]
            return checked_template.replace("{" + self.name + "}", value)

        return fill_inner

    def extract_value(self, ctx: Context, actor: Actor):
        self.value = self.func(ctx.last_request)
        return self.value


BaseSlot.update_forward_refs()
