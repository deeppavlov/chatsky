"""
Context
-------
Context is a data structure that is used to store information about the current state of a conversation.

It is used to keep track of the user's input, the current stage of the conversation, and any other
information that is relevant to the current context of a dialog.

The Context data structure provides several key features to make working with data easier.
Developers can use the context to store any information that is relevant to the current conversation,
such as user data, session data, conversation history, e.t.c.
This allows developers to easily access and use this data throughout the conversation flow.

Another important feature of the context is data serialization.
The context can be easily serialized to a format that can be stored or transmitted, such as JSON.
This allows developers to save the context data and resume the conversation later.
"""

from __future__ import annotations
from asyncio import Event, gather
from uuid import uuid4
from time import time_ns
from typing import Any, Callable, Optional, Dict, TYPE_CHECKING
import logging

from pydantic import BaseModel, Field, PrivateAttr, TypeAdapter, model_validator

from chatsky.context_storages.database import DBContextStorage
from chatsky.core.message import Message
from chatsky.slots.slots import SlotManager
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.ctx_dict import ContextDict

if TYPE_CHECKING:
    from chatsky.core.service import ComponentExecutionState
    from chatsky.core.script import Node
    from chatsky.core.pipeline import Pipeline

logger = logging.getLogger(__name__)


"""
class Turn(BaseModel):
    label: Optional[NodeLabel2Type] = Field(default=None)
    request: Optional[Message] = Field(default=None)
    response: Optional[Message] = Field(default=None)
"""


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


class Context(BaseModel):
    """
    A structure that is used to store data about the context of a dialog.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), exclude=True, frozen=True)
    """
    `id` is the unique context identifier. By default, randomly generated using `uuid4` is used.
    """
    _created_at: int = PrivateAttr(default_factory=time_ns)
    """
    Timestamp when the context was **first time saved to database**.
    It is set (and managed) by :py:class:`~chatsky.context_storages.DBContextStorage`.
    """
    _updated_at: int = PrivateAttr(default_factory=time_ns)
    """
    Timestamp when the context was **last time saved to database**.
    It is set (and managed) by :py:class:`~chatsky.context_storages.DBContextStorage`.
    """
    current_turn_id: int = Field(default=0)
    labels: ContextDict[int, AbsoluteNodeLabel] = Field(default_factory=ContextDict)
    requests: ContextDict[int, Message] = Field(default_factory=ContextDict)
    responses: ContextDict[int, Message] = Field(default_factory=ContextDict)
    """
    `turns` stores the history of all passed `labels`, `requests`, and `responses`.

        - key - `id` of the turn.
        - value - `label` on this turn.
    """
    misc: Dict[str, Any] = Field(default_factory=dict)
    """
    ``misc`` stores any custom data. The framework doesn't use this dictionary,
    so storage of any data won't reflect on the work of the internal Chatsky functions.

        - key - Arbitrary data name.
        - value - Arbitrary data.
    """
    framework_data: FrameworkData = Field(default_factory=FrameworkData)
    """
    This attribute is used for storing custom data required for pipeline execution.
    It is meant to be used by the framework only. Accessing it may result in pipeline breakage.
    """
    _storage: Optional[DBContextStorage] = PrivateAttr(None)

    @classmethod
    async def connected(
        cls, storage: DBContextStorage, start_label: Optional[AbsoluteNodeLabel] = None, id: Optional[str] = None
    ) -> Context:
        if id is None:
            uid = str(uuid4())
            logger.debug(f"Disconnected context created with uid: {uid}")
            instance = cls(id=uid)
            instance.requests = await ContextDict.new(storage, uid, storage._requests_field_name, Message)
            instance.responses = await ContextDict.new(storage, uid, storage._responses_field_name, Message)
            instance.labels = await ContextDict.new(storage, uid, storage._labels_field_name, AbsoluteNodeLabel)
            instance.labels[0] = start_label
            instance._storage = storage
            return instance
        else:
            if not isinstance(id, str):
                logger.warning(f"Id is not a string: {id}. Converting to string.")
                id = str(id)
            logger.debug(f"Connected context created with uid: {id}")
            main, labels, requests, responses = await gather(
                storage.load_main_info(id),
                ContextDict.connected(storage, id, storage._labels_field_name, AbsoluteNodeLabel),
                ContextDict.connected(storage, id, storage._requests_field_name, Message),
                ContextDict.connected(storage, id, storage._responses_field_name, Message),
            )
            if main is None:
                crt_at = upd_at = time_ns()
                turn_id = 0
                misc = dict()
                fw_data = FrameworkData()
                labels[0] = start_label
            else:
                turn_id, crt_at, upd_at, misc, fw_data = main
                misc = TypeAdapter(Dict[str, Any]).validate_json(misc)
                fw_data = FrameworkData.model_validate_json(fw_data)
            logger.debug(f"Context loaded with turns number: {len(labels)}")
            instance = cls(
                id=id,
                current_turn_id=turn_id,
                labels=labels,
                requests=requests,
                responses=responses,
                misc=misc,
                framework_data=fw_data,
            )
            instance._created_at, instance._updated_at, instance._storage = crt_at, upd_at, storage
            return instance

    async def delete(self) -> None:
        if self._storage is not None:
            await self._storage.delete_context(self.id)
        else:
            raise RuntimeError(f"{type(self).__name__} is not attached to any context storage!")

    @property
    def last_label(self) -> AbsoluteNodeLabel:
        if len(self.labels) == 0:
            raise ContextError("Labels are empty.")
        return self.labels._items[self.labels.keys()[-1]]

    @property
    def last_response(self) -> Message:
        if len(self.responses) == 0:
            raise ContextError("Responses are empty.")
        return self.responses._items[self.responses.keys()[-1]]

    @property
    def last_request(self) -> Message:
        if len(self.requests) == 0:
            raise ContextError("Requests are empty.")
        return self.requests._items[self.requests.keys()[-1]]

    @property
    def pipeline(self) -> Pipeline:
        """Return :py:attr:`.FrameworkData.pipeline`."""
        pipeline = self.framework_data.pipeline
        if pipeline is None:
            raise ContextError("Pipeline is not set.")
        return pipeline

    @property
    def current_node(self) -> Node:
        """Return :py:attr:`.FrameworkData.current_node`."""
        node = self.framework_data.current_node
        if node is None:
            raise ContextError("Current node is not set.")
        return node

    def __eq__(self, value: object) -> bool:
        if isinstance(value, Context):
            return (
                self.id == value.id
                and self.current_turn_id == value.current_turn_id
                and self.labels == value.labels
                and self.requests == value.requests
                and self.responses == value.responses
                and self.misc == value.misc
                and self.framework_data == value.framework_data
                and self._storage == value._storage
            )
        else:
            return False

    @model_validator(mode="wrap")
    def _validate_model(value: Any, handler: Callable[[Any], "Context"], _) -> "Context":
        if isinstance(value, Context):
            return value
        elif isinstance(value, Dict):
            instance = handler(value)
            labels_obj = value.get("labels", dict())
            if isinstance(labels_obj, Dict):
                labels_obj = TypeAdapter(Dict[int, AbsoluteNodeLabel]).validate_python(labels_obj)
            instance.labels = ContextDict.model_validate(labels_obj)
            instance.labels._ctx_id = instance.id
            requests_obj = value.get("requests", dict())
            if isinstance(requests_obj, Dict):
                requests_obj = TypeAdapter(Dict[int, Message]).validate_python(requests_obj)
            instance.requests = ContextDict.model_validate(requests_obj)
            instance.requests._ctx_id = instance.id
            responses_obj = value.get("responses", dict())
            if isinstance(responses_obj, Dict):
                responses_obj = TypeAdapter(Dict[int, Message]).validate_python(responses_obj)
            instance.responses = ContextDict.model_validate(responses_obj)
            instance.responses._ctx_id = instance.id
            return instance
        else:
            raise ValueError(f"Unknown type of Context value: {type(value).__name__}!")

    async def store(self) -> None:
        if self._storage is not None:
            logger.debug(f"Storing context: {self.id}...")
            self._updated_at = time_ns()
            misc_byted = self.framework_data.model_dump_json().encode()
            fw_data_byted = self.framework_data.model_dump_json().encode()
            await gather(
                self._storage.update_main_info(
                    self.id, self.current_turn_id, self._created_at, self._updated_at, misc_byted, fw_data_byted
                ),
                self.labels.store(),
                self.requests.store(),
                self.responses.store(),
            )
            logger.debug(f"Context stored: {self.id}")
        else:
            raise RuntimeError(f"{type(self).__name__} is not attached to any context storage!")
