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
from asyncio import gather
from uuid import uuid4
from time import time_ns
from typing import Any, Callable, Iterable, Optional, Dict, TYPE_CHECKING, Tuple, Union
import logging

from pydantic import BaseModel, Field, PrivateAttr, TypeAdapter, model_validator

from chatsky.context_storages.database import DBContextStorage, NameConfig
from chatsky.core.message import Message
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.ctx_dict import LabelContextDict, MessageContextDict
from chatsky.core.ctx_utils import ContextError, FrameworkData, ContextMainInfo

if TYPE_CHECKING:
    from chatsky.core.script import Node
    from chatsky.core.pipeline import Pipeline

logger = logging.getLogger(__name__)


class Context(ContextMainInfo):
    """
    A structure that is used to store data about the context of a dialog.
    """

    id: str = Field(default_factory=lambda: str(uuid4()), exclude=True, frozen=True)
    """
    `id` is the unique context identifier. By default, randomly generated using `uuid4` is used.
    """
    labels: LabelContextDict = Field(default_factory=LabelContextDict)
    """
    `labels` stores dialog labels.
    A new label is stored in the dictionary on every turn, the keys are consecutive integers.
    The first ever (initial) has key `0`.

        - key - Label identification numbers.
        - value - Label data: `AbsoluteNodeLabel`.
    """
    requests: MessageContextDict = Field(default_factory=MessageContextDict)
    """
    `requests` stores dialog requests.
    A new request is stored in the dictionary on every turn, the keys are consecutive integers.
    The first ever (initial) has key `1`.

        - key - Request identification numbers.
        - value - Request data: `Message`.
    """
    responses: MessageContextDict = Field(default_factory=MessageContextDict)
    """
    `responses` stores dialog responses.
    A new response is stored in the dictionary on every turn, the keys are consecutive integers.
    The first ever (initial) has key `1`.

        - key - Response identification numbers.
        - value - Response data: `Message`.
    """
    _storage: Optional[DBContextStorage] = PrivateAttr(None)
    """
    Context storage this context is connected to (if any).
    """

    @classmethod
    async def connected(
        cls, storage: DBContextStorage, start_label: Optional[AbsoluteNodeLabel] = None, id: Optional[str] = None
    ) -> Context:
        """
        Create context **connected** to the given database storage.
        If context ID is given, the corresponding context is loaded from the database.
        If the context does not exist in database or ID is `None`, a new context with new ID is created.
        A connected context can be later stored in the database.

        :param storage: context storage to connect to.
        :param start_label: new context start label (will be set only if the context is created).
        :param id: context ID.
        :return: context, connected to the database.
        """

        if id is None:
            uid = str(uuid4())
            logger.debug(f"Disconnected context created with uid: {uid}")
            instance = cls(id=uid)
            instance.requests = await MessageContextDict.new(storage, uid, NameConfig._requests_field)
            instance.responses = await MessageContextDict.new(storage, uid, NameConfig._responses_field)
            instance.labels = await LabelContextDict.new(storage, uid, NameConfig._labels_field)
            await instance.labels.update({0: start_label})
            instance._storage = storage
            return instance
        else:
            if not isinstance(id, str):
                logger.warning(f"Id is not a string: {id}. Converting to string.")
                id = str(id)
            logger.debug(f"Connected context created with uid: {id}")
            main, labels, requests, responses = await gather(
                storage.load_main_info(id),
                LabelContextDict.connected(storage, id, NameConfig._labels_field),
                MessageContextDict.connected(storage, id, NameConfig._requests_field),
                MessageContextDict.connected(storage, id, NameConfig._responses_field),
            )
            if main is None:
                crt_at = upd_at = time_ns()
                current_turn_id = 0
                misc = dict()
                fw_data = FrameworkData()
                labels[0] = start_label
            else:
                current_turn_id = main.current_turn_id
                crt_at = main.created_at
                upd_at = main.updated_at
                misc = main.misc
                fw_data = main.framework_data
            logger.debug(f"Context loaded with turns number: {len(labels)}")
            instance = cls(
                id=id,
                current_turn_id=current_turn_id,
                created_at=crt_at,
                updated_at=upd_at,
                misc=misc,
                framework_data=fw_data,
                labels=labels,
                requests=requests,
                responses=responses,
            )
            instance._storage = storage
            return instance

    async def delete(self) -> None:
        """
        Delete connected context from the context storage and disconnect it.
        Throw an error if the context is not connected.
        No local context fields will be affected.
        If the context is not connected, throw a runtime error.
        """

        if self._storage is not None:
            await self._storage.delete_context(self.id)
            self._storage = None
        else:
            raise RuntimeError(f"{type(self).__name__} is not attached to any context storage!")

    @property
    def last_label(self) -> AbsoluteNodeLabel:
        """
        Receive last turn label.
        Throw an error if no labels are present or the last label is absent.
        :return: The last turn label.
        """

        if len(self.labels) == 0:
            raise ContextError("Labels are empty.")
        return self.labels._items[self.labels.keys()[-1]]

    @property
    def last_response(self) -> Message:
        """
        Receive last turn response.
        Throw an error if no responses are present or the last response is absent.
        :return: The last turn response.
        """

        if len(self.responses) == 0:
            raise ContextError("Responses are empty.")
        return self.responses._items[self.responses.keys()[-1]]

    @property
    def last_request(self) -> Message:
        """
        Receive last turn request.
        Throw an error if no requests are present or the last request is absent.
        :return: The last turn request.
        """

        if len(self.requests) == 0:
            raise ContextError("Requests are empty.")
        return self.requests._items[self.requests.keys()[-1]]

    @property
    def pipeline(self) -> Pipeline:
        """
        Return :py:attr:`.FrameworkData.pipeline`.
        """

        pipeline = self.framework_data.pipeline
        if pipeline is None:
            raise ContextError("Pipeline is not set.")
        return pipeline

    @property
    def current_node(self) -> Node:
        """
        Return :py:attr:`.FrameworkData.current_node`.
        """

        node = self.framework_data.current_node
        if node is None:
            raise ContextError("Current node is not set.")
        return node

    async def turns(self, key: Union[int, slice]) -> Iterable[Tuple[AbsoluteNodeLabel, Message, Message]]:
        """
        Get one or more nodes, requests and responses sharing common keys simultaneously.
        Acts just like context dict `get` method, but queries all three dicts at the same time asinchronously.
        :param key: Context dict key that will be queried from `labels`, `requests` and `responses`.
        :return: Tuples of (`label`, `request`, `response`), sharing a common key.
        """

        turn_ids = range(self.current_turn_id + 1)[key]
        turn_ids = turn_ids if isinstance(key, slice) else [turn_ids]
        context_dicts = (self.labels, self.requests, self.responses)
        turns_lists = await gather(*[gather(*[ctd.get(ti, None) for ti in turn_ids]) for ctd in context_dicts])
        return zip(*turns_lists)

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

    def __copy__(self):
        storage = self._storage
        self._storage = None
        copy = BaseModel.__copy__(self)
        copy._storage = self._storage = storage
        return copy

    def __deepcopy__(self, memo: dict[int, Any] | None = None):
        storage = self._storage
        self._storage = None
        copy = BaseModel.__deepcopy__(self, memo)
        copy._storage = self._storage = storage
        return copy

    @model_validator(mode="wrap")
    def _validate_model(value: Any, handler: Callable[[Any], "Context"], _) -> "Context":
        if isinstance(value, Context):
            return value
        elif isinstance(value, Dict):
            instance = handler(value)
            labels_obj = value.get("labels", dict())
            if isinstance(labels_obj, Dict):
                labels_obj = TypeAdapter(Dict[int, AbsoluteNodeLabel]).validate_python(labels_obj)
            instance.labels = LabelContextDict.model_validate(labels_obj)
            instance.labels._ctx_id = instance.id
            requests_obj = value.get("requests", dict())
            if isinstance(requests_obj, Dict):
                requests_obj = TypeAdapter(Dict[int, Message]).validate_python(requests_obj)
            instance.requests = MessageContextDict.model_validate(requests_obj)
            instance.requests._ctx_id = instance.id
            responses_obj = value.get("responses", dict())
            if isinstance(responses_obj, Dict):
                responses_obj = TypeAdapter(Dict[int, Message]).validate_python(responses_obj)
            instance.responses = MessageContextDict.model_validate(responses_obj)
            instance.responses._ctx_id = instance.id
            return instance
        else:
            raise ValueError(f"Unknown type of Context value: {type(value).__name__}!")

    async def store(self) -> None:
        """
        Store connected context in the context storage.
        Depending on the context storage settings ("rewrite_existing" flag in particular),
        either only write new and deleted values or also modify the changed ones.
        All the context storage tables are updated asynchronously and simultaneously.
        """

        if self._storage is not None:
            logger.debug(f"Storing context: {self.id}...")
            main_into = ContextMainInfo(
                current_turn_id=self.current_turn_id,
                created_at=self.created_at,
                updated_at=time_ns(),
                misc=self.misc,
                framework_data=self.framework_data,
            )
            labels_data = self.labels.extract_sync()
            requests_data = self.requests.extract_sync()
            responses_data = self.responses.extract_sync()
            await self._storage.update_context(self.id, main_into, [labels_data, requests_data, responses_data])
            logger.debug(f"Context stored: {self.id}")
        else:
            raise RuntimeError(f"{type(self).__name__} is not attached to any context storage!")
