from __future__ import annotations
from asyncio import Event
from json import loads
from time import time_ns
from typing import Any, Optional, Dict, TYPE_CHECKING

from pydantic import BaseModel, Field, PrivateAttr, TypeAdapter, field_serializer, field_validator

from chatsky.slots.slots import SlotManager

if TYPE_CHECKING:
    from chatsky.core.service import ComponentExecutionState
    from chatsky.core.script import Node
    from chatsky.core.pipeline import Pipeline


class ContextError(Exception):
    """Raised when context methods are not used correctly."""


class ServiceState(BaseModel, arbitrary_types_allowed=True):
    execution_status: ComponentExecutionState = Field(default="NOT_RUN")
    """
    :py:class:`.ComponentExecutionState` of this pipeline service.
    Cleared at the end of every turn.
    """
    finished_event: Event = Field(default_factory=Event)
    """
    Asyncio `Event` which can be awaited until this service finishes.
    Cleared at the end of every turn.
    """


class FrameworkData(BaseModel, arbitrary_types_allowed=True):
    """
    Framework uses this to store data related to any of its modules.
    """

    service_states: Dict[str, ServiceState] = Field(default_factory=dict, exclude=True)
    """
    Dictionary containing :py:class:`.ServiceState` of all the pipeline components.
    Cleared at the end of every turn.
    """
    current_node: Optional[Node] = Field(default=None, exclude=True)
    """
    A copy of the current node provided by :py:meth:`~chatsky.core.script.Script.get_inherited_node`.
    This node can be safely modified by Processing functions to alter current node fields.
    """
    pipeline: Optional[Pipeline] = Field(default=None, exclude=True)
    """
    Instance of the pipeline that manages this context.
    Can be used to obtain run configuration such as script or fallback label.
    """
    stats: Dict[str, Any] = Field(default_factory=dict)
    "Enables complex stats collection across multiple turns."
    slot_manager: SlotManager = Field(default_factory=SlotManager)
    "Stores extracted slots."


class ContextMainInfo(BaseModel):
    """
    Main context fields, that are stored in `MAIN` table.
    For most of the database backends, it will be serialized to json.
    For SQL database backends, it will be written to different table columns.
    For memory context storage, it won't be serialized at all.
    """

    current_turn_id: int
    created_at: int = Field(default_factory=time_ns)
    updated_at: int = Field(default_factory=time_ns)
    misc: Dict[str, Any] = Field(default_factory=dict)
    framework_data: FrameworkData = Field(default_factory=dict, validate_default=True)

    _misc_adaptor: TypeAdapter[Dict[str, Any]] = PrivateAttr(default=TypeAdapter(Dict[str, Any]))

    @field_validator("framework_data", "misc", mode="before")
    @classmethod
    def _validate_framework_data(cls, value: Any) -> Dict:
        if isinstance(value, bytes) or isinstance(value, str):
            value = loads(value)
        return value

    @field_serializer("misc", when_used="always")
    def _serialize_misc(self, misc: Dict[str, Any]) -> bytes:
        return self._misc_adaptor.dump_json(misc)

    @field_serializer("framework_data", when_used="always")
    def _serialize_framework_data(self, framework_data: FrameworkData) -> bytes:
        return framework_data.model_dump_json().encode()

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BaseModel):
            return self.model_dump() == other.model_dump()
        return super().__eq__(other)
