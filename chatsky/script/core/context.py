"""
Context
-------
A Context is a data structure that is used to store information about the current state of a conversation.
It is used to keep track of the user's input, the current stage of the conversation, and any other
information that is relevant to the current context of a dialog.
The Context provides a convenient interface for working with data, allowing developers to easily add,
retrieve, and manipulate data as the conversation progresses.

The Context data structure provides several key features to make working with data easier.
Developers can use the context to store any information that is relevant to the current conversation,
such as user data, session data, conversation history, or etc.
This allows developers to easily access and use this data throughout the conversation flow.

Another important feature of the context is data serialization.
The context can be easily serialized to a format that can be stored or transmitted, such as JSON.
This allows developers to save the context data and resume the conversation later.
"""

from __future__ import annotations
import logging
from uuid import uuid4
from time import time_ns
from typing import Any, Optional, Union, Dict, List, Set, TYPE_CHECKING

from pydantic import BaseModel, Field, PrivateAttr

from chatsky.context_storages.database import DBContextStorage
from chatsky.script.core.message import Message
from chatsky.script.core.types import NodeLabel2Type
from chatsky.pipeline.types import ComponentExecutionState
from chatsky.slots.slots import SlotManager
from chatsky.utils.context_dict import ContextDict, launch_coroutines

if TYPE_CHECKING:
    from chatsky.script.core.script import Node

logger = logging.getLogger(__name__)

"""
class Turn(BaseModel):
    label: Optional[NodeLabel2Type] = Field(default=None)
    request: Optional[Message] = Field(default=None)
    response: Optional[Message] = Field(default=None)
"""


class FrameworkData(BaseModel):
    """
    Framework uses this to store data related to any of its modules.
    """

    service_states: Dict[str, ComponentExecutionState] = Field(default_factory=dict, exclude=True)
    "Statuses of all the pipeline services. Cleared at the end of every turn."
    actor_data: Dict[str, Any] = Field(default_factory=dict, exclude=True)
    "Actor service data. Cleared at the end of every turn."
    stats: Dict[str, Any] = Field(default_factory=dict)
    "Enables complex stats collection across multiple turns."
    slot_manager: SlotManager = Field(default_factory=SlotManager)
    "Stores extracted slots."


class Context(BaseModel):
    """
    A structure that is used to store data about the context of a dialog.

    Avoid storing unserializable data in the fields of this class in order for
    context storages to work.
    """

    primary_id: str = Field(default_factory=lambda: str(uuid4()), exclude=True, frozen=True)
    """
    `primary_id` is the unique context identifier. By default, randomly generated using `uuid4` is used.
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
    labels: ContextDict[int, NodeLabel2Type] = Field(default_factory=ContextDict)
    requests: ContextDict[int, Message] = Field(default_factory=ContextDict)
    responses: ContextDict[int, Message] = Field(default_factory=ContextDict)
    """
    `turns` stores the history of all passed `labels`, `requests`, and `responses`.

        - key - `id` of the turn.
        - value - `label` on this turn.
    """
    misc: ContextDict[str, Any] = Field(default_factory=ContextDict)
    """
    `misc` stores any custom data. The scripting doesn't use this dictionary by default,
    so storage of any data won't reflect on the work on the internal Chatsky Scripting functions.

    Avoid storing unserializable data in order for context storages to work.

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
    async def connect(cls, id: Optional[str], storage: Optional[DBContextStorage] = None) -> Context:
        if storage is None:
            return cls(id=id)
        else:
            main, labels, requests, responses, misc = await launch_coroutines(
                [
                    storage.load_main_info(id),
                    ContextDict.connected(storage, id, storage.labels_config.name, tuple),
                    ContextDict.connected(storage, id, storage.requests_config.name, Message.model_validate),
                    ContextDict.connected(storage, id, storage.responses_config.name, Message.model_validate),
                    ContextDict.connected(storage, id, storage.misc_config.name)
                ],
                storage.is_asynchronous,
            )
            if main is None:
                raise ValueError(f"Context with id {id} not found in the storage!")
            crt_at, upd_at, fw_data = main
            objected = storage.serializer.loads(fw_data)
            instance = cls(id=id, framework_data=objected, labels=labels, requests=requests, responses=responses, misc=misc)
            instance._created_at, instance._updated_at, instance._storage = crt_at, upd_at, storage
            return instance

    async def store(self) -> None:
        if self._storage is not None:
            self._updated_at = time_ns()
            byted = self._storage.serializer.dumps(self.framework_data)
            await launch_coroutines(
                [
                    self._storage.update_main_info(self.primary_id, self._created_at, self._updated_at, byted),
                    self.labels.store(),
                    self.requests.store(),
                    self.responses.store(),
                    self.misc.store(),
                ],
                self._storage.is_asynchronous,
            )
        else:
            raise RuntimeError(f"{type(self).__name__} is not attached to any context storage!")

    def clear(
        self,
        hold_last_n_indices: int,
        field_names: Union[Set[str], List[str]] = {"labels", "requests", "responses"},
    ):
        field_names = field_names if isinstance(field_names, set) else set(field_names)
        if "labels" in field_names:
            del self.labels[:-hold_last_n_indices]
        if "requests" in field_names:
            del self.requests[:-hold_last_n_indices]
        if "responses" in field_names:
            del self.responses[:-hold_last_n_indices]
        if "misc" in field_names:
            self.misc.clear()
        if "framework_data" in field_names:
            self.framework_data = FrameworkData()

    async def delete(self) -> None:
        if self._storage is not None:
            await self._storage.delete_main_info(self.primary_id)
        else:
            raise RuntimeError(f"{type(self).__name__} is not attached to any context storage!")

    def add_turn_items(self, label: Optional[NodeLabel2Type] = None, request: Optional[Message] = None, response: Optional[Message] = None):
        self.labels[max(self.labels.keys(), default=-1) + 1] = label
        self.requests[max(self.requests.keys(), default=-1) + 1] = request
        self.responses[max(self.responses.keys(), default=-1) + 1] = response

    @property
    def last_label(self) -> Optional[NodeLabel2Type]:
        label_keys = [k for k in self.labels._items.keys() if self.labels._items[k] is not None]
        return self.labels._items.get(max(label_keys, default=None), None)

    @last_label.setter
    def last_label(self, label: Optional[NodeLabel2Type]):
        self.labels[max(self.labels.keys(), default=0)] = label

    @property
    def last_response(self) -> Optional[Message]:
        response_keys = [k for k in self.responses._items.keys() if self.responses._items[k] is not None]
        return self.responses._items.get(max(response_keys, default=None), None)

    @last_response.setter
    def last_response(self, response: Optional[Message]):
        self.responses[max(self.responses.keys(), default=0)] = response

    @property
    def last_request(self) -> Optional[Message]:
        request_keys = [k for k in self.requests._items.keys() if self.requests._items[k] is not None]
        return self.requests._items.get(max(request_keys, default=None), None)

    @last_request.setter
    def last_request(self, request: Optional[Message]):
        self.requests[max(self.requests.keys(), default=0)] = request

    @property
    def current_node(self) -> Optional[Node]:
        """
        Return current :py:class:`~chatsky.script.core.script.Node`.
        """
        actor_data = self.framework_data.actor_data
        node = (
            actor_data.get("processed_node")
            or actor_data.get("pre_response_processed_node")
            or actor_data.get("next_node")
            or actor_data.get("pre_transitions_processed_node")
            or actor_data.get("previous_node")
        )
        if node is None:
            logger.warning(
                "The `current_node` method should be called "
                "when an actor is running between the "
                "`ActorStage.GET_PREVIOUS_NODE` and `ActorStage.FINISH_TURN` stages."
            )

        return node

    def __eq__(self, value: object) -> bool:
        if isinstance(value, Context):
            return (
                self.primary_id == value.primary_id
                and self.labels == value.labels
                and self.requests == value.requests
                and self.responses == value.responses
                and self.misc == value.misc
                and self.framework_data == value.framework_data
                and self._storage == value._storage
            )
        else:
            return False
