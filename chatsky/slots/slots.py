"""
Slots
-----
This module defines base classes for slots and some concrete implementations of them.
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Callable, Any, Awaitable, TYPE_CHECKING, Union, Optional, Dict
from typing_extensions import TypeAlias, Annotated
import logging
from functools import reduce
from string import Formatter

from pydantic import BaseModel, model_validator, Field, field_serializer, field_validator

from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from chatsky.utils.devel.json_serialization import pickle_serializer, pickle_validator

if TYPE_CHECKING:
    from chatsky.core import Context, Message


logger = logging.getLogger(__name__)


SlotName: TypeAlias = str
"""
A string to identify slots.

Top-level slots are identified by their key in a :py:class:`~.GroupSlot`.

E.g.

.. code:: python

    GroupSlot(
        user=RegexpSlot(),
        password=FunctionSlot,
    )

Has two slots with names "user" and "password".

For nested group slots use dots to separate names:

.. code:: python

    GroupSlot(
        user=GroupSlot(
            name=FunctionSlot,
            password=FunctionSlot,
        )
    )

Has two slots with names "user.name" and "user.password".
"""


def recursive_getattr(obj, slot_name: SlotName):
    def two_arg_getattr(__o, name):
        # pydantic handles exception when accessing a non-existing extra-field on its own
        # return None by default to avoid that
        return getattr(__o, name, None)

    return reduce(two_arg_getattr, [obj, *slot_name.split(".")])


def recursive_setattr(obj, slot_name: SlotName, value):
    parent_slot, sep, slot = slot_name.rpartition(".")

    if sep == ".":
        parent_obj = recursive_getattr(obj, parent_slot)
    else:
        parent_obj = obj

    if isinstance(value, ExtractedGroupSlot):
        getattr(parent_obj, slot).update(value)
    else:
        setattr(parent_obj, slot, value)


class SlotNotExtracted(Exception):
    """This exception can be returned or raised by slot extractor if slot extraction is unsuccessful."""

    pass


class ExtractedSlot(BaseModel, ABC):
    """
    Represents value of an extracted slot.

    Instances of this class are managed by framework and
    are stored in :py:attr:`~chatsky.core.context.FrameworkData.slot_manager`.
    They can be accessed via the ``ctx.framework_data.slot_manager.get_extracted_slot`` method.
    """

    @property
    @abstractmethod
    def __slot_extracted__(self) -> bool:
        """Whether the slot is extracted."""
        raise NotImplementedError

    def __unset__(self):
        """Mark slot as not extracted and clear extracted data (except for default value)."""
        raise NotImplementedError

    @abstractmethod
    def __str__(self):
        """String representation is used to fill templates."""
        raise NotImplementedError


class ExtractedValueSlot(ExtractedSlot):
    """Value extracted from :py:class:`~.ValueSlot`."""

    is_slot_extracted: bool
    extracted_value: Any
    default_value: Any = None

    @field_serializer("extracted_value", "default_value", when_used="json")
    def pickle_serialize_values(self, value):
        """
        Cast values to string via pickle.
        Allows storing arbitrary data in these fields when using context storages.
        """
        if value is not None:
            return pickle_serializer(value)
        return value

    @field_validator("extracted_value", "default_value", mode="before")
    @classmethod
    def pickle_validate_values(cls, value):
        """
        Restore values after being processed with
        :py:meth:`pickle_serialize_values`.
        """
        if value is not None:
            return pickle_validator(value)
        return value

    @property
    def __slot_extracted__(self) -> bool:
        return self.is_slot_extracted

    def __unset__(self):
        self.is_slot_extracted = False
        self.extracted_value = SlotNotExtracted("Slot manually unset.")

    @property
    def value(self):
        """Extracted value or the default value if the slot is not extracted."""
        return self.extracted_value if self.is_slot_extracted else self.default_value

    def __str__(self):
        return str(self.value)


class ExtractedGroupSlot(ExtractedSlot, extra="allow"):
    __pydantic_extra__: Dict[
        str, Annotated[Union["ExtractedGroupSlot", "ExtractedValueSlot"], Field(union_mode="left_to_right")]
    ]

    @property
    def __slot_extracted__(self) -> bool:
        return all([slot.__slot_extracted__ for slot in self.__pydantic_extra__.values()])

    def __unset__(self):
        for child in self.__pydantic_extra__.values():
            child.__unset__()

    def __str__(self):
        return str({key: str(value) for key, value in self.__pydantic_extra__.items()})

    def update(self, old: "ExtractedGroupSlot"):
        """
        Rebase this extracted groups slot on top of another one.
        This is required to merge slot storage in-context
        with a potentially different slot configuration passed to pipeline.

        :param old: An instance of :py:class:`~.ExtractedGroupSlot` stored in-context.
            Extracted values will be transferred to this object.
        """
        for slot in old.__pydantic_extra__:
            if slot in self.__pydantic_extra__:
                new_slot = self.__pydantic_extra__[slot]
                old_slot = old.__pydantic_extra__[slot]
                if isinstance(new_slot, ExtractedGroupSlot) and isinstance(old_slot, ExtractedGroupSlot):
                    new_slot.update(old_slot)
                if isinstance(new_slot, ExtractedValueSlot) and isinstance(old_slot, ExtractedValueSlot):
                    self.__pydantic_extra__[slot] = old_slot


class BaseSlot(BaseModel, frozen=True):
    """
    BaseSlot is a base class for all slots.
    """

    @abstractmethod
    async def get_value(self, ctx: Context) -> ExtractedSlot:
        """
        Extract slot value from :py:class:`~.Context` and return an instance of :py:class:`~.ExtractedSlot`.
        """
        raise NotImplementedError

    @abstractmethod
    def init_value(self) -> ExtractedSlot:
        """
        Provide an initial value to fill slot storage with.
        """
        raise NotImplementedError


class ValueSlot(BaseSlot, frozen=True):
    """
    Value slot is a base class for all slots that are designed to extract concrete values.
    Subclass it, if you want to declare your own slot type.
    """

    default_value: Any = None

    @abstractmethod
    async def extract_value(self, ctx: Context) -> Union[Any, SlotNotExtracted]:
        """
        Return value extracted from context.

        Return :py:exc:`~.SlotNotExtracted` to mark extraction as unsuccessful.

        Raising exceptions is also allowed and will result in an unsuccessful extraction as well.
        """
        raise NotImplementedError

    async def get_value(self, ctx: Context) -> ExtractedValueSlot:
        """Wrapper for :py:meth:`~.ValueSlot.extract_value` to handle exceptions."""
        extracted_value = SlotNotExtracted("Caught an exit exception.")
        is_slot_extracted = False

        try:
            extracted_value = await wrap_sync_function_in_async(self.extract_value, ctx)
            is_slot_extracted = not isinstance(extracted_value, SlotNotExtracted)
        except Exception as error:
            logger.exception(f"Exception occurred during {self.__class__.__name__!r} extraction.", exc_info=error)
            extracted_value = error
        finally:
            if not is_slot_extracted:
                logger.debug(f"Slot {self.__class__.__name__!r} was not extracted: {extracted_value}")
            return ExtractedValueSlot.model_construct(
                is_slot_extracted=is_slot_extracted,
                extracted_value=extracted_value,
                default_value=self.default_value,
            )

    def init_value(self) -> ExtractedValueSlot:
        return ExtractedValueSlot.model_construct(
            is_slot_extracted=False,
            extracted_value=SlotNotExtracted("Initial slot extraction."),
            default_value=self.default_value,
        )


class GroupSlot(BaseSlot, extra="allow", frozen=True):
    """
    Base class for :py:class:`~.RootSlot` and :py:class:`~.GroupSlot`.
    """

    __pydantic_extra__: Dict[str, Annotated[Union["GroupSlot", "ValueSlot"], Field(union_mode="left_to_right")]]
    allow_partial_extraction: bool = False
    """If True, extraction returns only successfully extracted child slots."""

    def __init__(self, allow_partial_extraction=False, **kwargs):
        super().__init__(allow_partial_extraction=allow_partial_extraction, **kwargs)

    @model_validator(mode="after")
    def __check_extra_field_names__(self):
        """
        Extra field names cannot be dunder names or contain dots.
        """
        for field in self.__pydantic_extra__.keys():
            if "." in field:
                raise ValueError(f"Extra field name cannot contain dots: {field!r}")
            if field.startswith("__") and field.endswith("__"):
                raise ValueError(f"Extra field names cannot be dunder: {field!r}")
        return self

    async def get_value(self, ctx: Context) -> ExtractedGroupSlot:
        child_values = await asyncio.gather(*(child.get_value(ctx) for child in self.__pydantic_extra__.values()))
        extracted_values = {}
        for child_value, child_name in zip(child_values, self.__pydantic_extra__.keys()):
            if child_value.__slot_extracted__ or not self.allow_partial_extraction:
                extracted_values[child_name] = child_value

        return ExtractedGroupSlot(**extracted_values)

    def init_value(self) -> ExtractedGroupSlot:
        return ExtractedGroupSlot(
            **{child_name: child.init_value() for child_name, child in self.__pydantic_extra__.items()}
        )


class RegexpSlot(ValueSlot, frozen=True):
    """
    RegexpSlot is a slot type that extracts its value using a regular expression.
    You can pass a compiled or a non-compiled pattern to the `regexp` argument.
    If you want to extract a particular group, but not the full match,
    change the `match_group_idx` parameter.
    """

    regexp: str
    match_group_idx: int = 0
    "Index of the group to match."

    async def extract_value(self, ctx: Context) -> Union[str, SlotNotExtracted]:
        request_text = ctx.last_request.text
        search = re.search(self.regexp, request_text)
        return (
            search.group(self.match_group_idx)
            if search
            else SlotNotExtracted(f"Failed to match pattern {self.regexp!r} in {request_text!r}.")
        )


class FunctionSlot(ValueSlot, frozen=True):
    """
    A simpler version of :py:class:`~.ValueSlot`.

    Uses a user-defined `func` to extract slot value from the :py:attr:`~.Context.last_request` Message.
    """

    func: Callable[[Message], Union[Awaitable[Union[Any, SlotNotExtracted]], Any, SlotNotExtracted]]

    async def extract_value(self, ctx: Context) -> Union[Any, SlotNotExtracted]:
        return await wrap_sync_function_in_async(self.func, ctx.last_request)


class SlotManager(BaseModel):
    """
    Provides API for managing slots.

    An instance of this class can be accessed via ``ctx.framework_data.slot_manager``.
    """

    slot_storage: ExtractedGroupSlot = Field(default_factory=ExtractedGroupSlot)
    """Slot storage. Stored inside ctx.framework_data."""
    root_slot: GroupSlot = Field(default_factory=GroupSlot, exclude=True)
    """Slot configuration passed during pipeline initialization."""

    def set_root_slot(self, root_slot: GroupSlot):
        """
        Set root_slot configuration from pipeline.
        Update extracted slots with the new configuration:

        New slots are added with their :py:meth:`~.BaseSlot.init_value`.
        Old extracted slot values are preserved only if their configuration did not change.
        That is if they are still present in the config and if their fundamental type did not change
        (i.e. `GroupSlot` did not turn into a `ValueSlot` or vice versa).

        This method is called by pipeline and is not supposed to be used otherwise.
        """
        self.root_slot = root_slot
        new_slot_storage = root_slot.init_value()
        new_slot_storage.update(self.slot_storage)
        self.slot_storage = new_slot_storage

    def get_slot(self, slot_name: SlotName) -> BaseSlot:
        """
        Get slot configuration from the slot name.

        :raises KeyError: If the slot with the specified name does not exist.
        """
        slot = recursive_getattr(self.root_slot, slot_name)
        if isinstance(slot, BaseSlot):
            return slot
        raise KeyError(f"Could not find slot {slot_name!r}.")

    async def extract_slot(self, slot_name: SlotName, ctx: Context, success_only: bool) -> None:
        """
        Extract slot `slot_name` and store extracted value in `slot_storage`.

        Extracted group slots update slot storage instead of overwriting it.

        :raises KeyError: If the slot with the specified name does not exist.

        :param slot_name: Name of the slot to extract.
        :param ctx: Context.
        :param success_only: Whether to store the value only if it is successfully extracted.
        """
        slot = self.get_slot(slot_name)
        value = await slot.get_value(ctx)

        if value.__slot_extracted__ or success_only is False:
            recursive_setattr(self.slot_storage, slot_name, value)

    async def extract_all(self, ctx: Context):
        """
        Extract all slots from slot configuration `root_slot` and set `slot_storage` to the extracted value.
        """
        self.slot_storage = await self.root_slot.get_value(ctx)

    def get_extracted_slot(self, slot_name: SlotName) -> Union[ExtractedValueSlot, ExtractedGroupSlot]:
        """
        Retrieve extracted value from `slot_storage`.

        :raises KeyError: If the slot with the specified name does not exist.
        """
        slot = recursive_getattr(self.slot_storage, slot_name)
        if isinstance(slot, ExtractedSlot):
            return slot
        raise KeyError(f"Could not find slot {slot_name!r}.")

    def is_slot_extracted(self, slot_name: str) -> bool:
        """
        Return if the specified slot is extracted.

        :raises KeyError: If the slot with the specified name does not exist.
        """
        return self.get_extracted_slot(slot_name).__slot_extracted__

    def all_slots_extracted(self) -> bool:
        """
        Return if all slots are extracted.
        """
        return self.slot_storage.__slot_extracted__

    def unset_slot(self, slot_name: SlotName) -> None:
        """
        Mark specified slot as not extracted and clear extracted value.

        :raises KeyError: If the slot with the specified name does not exist.
        """
        self.get_extracted_slot(slot_name).__unset__()

    def unset_all_slots(self) -> None:
        """
        Mark all slots as not extracted and clear all extracted values.
        """
        self.slot_storage.__unset__()

    class KwargOnlyFormatter(Formatter):
        def get_value(self, key, args, kwargs):
            return super().get_value(str(key), args, kwargs)

    def fill_template(self, template: str) -> Optional[str]:
        """
        Fill `template` string with extracted slot values and return a formatted string
        or None if an exception has occurred while trying to fill template.

        `template` should be a format-string:

        E.g. "Your username is {profile.username}".

        For the example above, if ``profile.username`` slot has value "admin",
        it would return the following text:
        "Your username is admin".
        """
        try:
            return self.KwargOnlyFormatter().format(template, **dict(self.slot_storage.__pydantic_extra__.items()))
        except Exception as exc:
            logger.exception("An exception occurred during template filling.", exc_info=exc)
            return None
