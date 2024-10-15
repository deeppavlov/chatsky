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
import logging
import asyncio
from uuid import UUID, uuid4
from typing import Any, Optional, Union, Dict, TYPE_CHECKING

from pydantic import BaseModel, Field

from chatsky.core.message import Message, MessageInitTypes
from chatsky.slots.slots import SlotManager
from chatsky.core.node_label import AbsoluteNodeLabel, AbsoluteNodeLabelInitTypes

if TYPE_CHECKING:
    from chatsky.core.service import ComponentExecutionState
    from chatsky.core.script import Node
    from chatsky.core.pipeline import Pipeline

logger = logging.getLogger(__name__)


def get_last_index(dictionary: dict) -> int:
    """
    Obtain the last index from the `dictionary`.

    :param dictionary: Dictionary with unsorted keys.
    :return: Last index from the `dictionary`.
    :raises ValueError: If the dictionary is empty.
    """
    if len(dictionary) == 0:
        raise ValueError("Dictionary is empty.")
    indices = list(dictionary)
    return max(indices)


class ContextError(Exception):
    """Raised when context methods are not used correctly."""


class ServiceState(BaseModel, arbitrary_types_allowed=True):
    execution_status: ComponentExecutionState = Field(default="NOT_RUN")
    """
    :py:class:`.ComponentExecutionState` of this pipeline service.
    Cleared at the end of every turn.
    """
    finished_event: asyncio.Event = Field(default_factory=asyncio.Event)
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

    id: Union[UUID, int, str] = Field(default_factory=uuid4)
    """
    ``id`` is the unique context identifier. By default, randomly generated using ``uuid4``.
    ``id`` can be used to trace the user behavior, e.g while collecting the statistical data.
    """
    labels: Dict[int, AbsoluteNodeLabel] = Field(default_factory=dict)
    """
    ``labels`` stores the history of labels for all passed nodes.

        - key - ``id`` of the turn.
        - value - ``label`` of this turn.

    Start label is stored at key ``0``.
    IDs go up by ``1`` after that.
    """
    requests: Dict[int, Message] = Field(default_factory=dict)
    """
    ``requests`` stores the history of all requests received by the pipeline.

        - key - ``id`` of the turn.
        - value - ``request`` of this turn.

    First request is stored at key ``1``.
    IDs go up by ``1`` after that.
    """
    responses: Dict[int, Message] = Field(default_factory=dict)
    """
    ``responses`` stores the history of all responses produced by the pipeline.

        - key - ``id`` of the turn.
        - value - ``response`` of this turn.

    First response is stored at key ``1``.
    IDs go up by ``1`` after that.
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

    @classmethod
    def init(cls, start_label: AbsoluteNodeLabelInitTypes, id: Optional[Union[UUID, int, str]] = None):
        """Initialize new context from ``start_label`` and, optionally, context ``id``."""
        init_kwargs = {
            "labels": {0: AbsoluteNodeLabel.model_validate(start_label)},
        }
        if id is None:
            return cls(**init_kwargs)
        else:
            return cls(**init_kwargs, id=id)

    def add_request(self, request: MessageInitTypes):
        """
        Add a new ``request`` to the context.
        """
        request_message = Message.model_validate(request)
        if len(self.requests) == 0:
            self.requests[1] = request_message
        else:
            last_index = get_last_index(self.requests)
            self.requests[last_index + 1] = request_message

    def add_response(self, response: MessageInitTypes):
        """
        Add a new ``response`` to the context.
        """
        response_message = Message.model_validate(response)
        if len(self.responses) == 0:
            self.responses[1] = response_message
        else:
            last_index = get_last_index(self.responses)
            self.responses[last_index + 1] = response_message

    def add_label(self, label: AbsoluteNodeLabelInitTypes):
        """
        Add a new :py:class:`~.AbsoluteNodeLabel` to the context.

        :raises ContextError: If :py:attr:`labels` is empty.
        """
        label = AbsoluteNodeLabel.model_validate(label)
        if len(self.labels) == 0:
            raise ContextError("Labels are empty. Use `Context.init` to initialize context with labels.")
        last_index = get_last_index(self.labels)
        self.labels[last_index + 1] = label

    @property
    def last_label(self) -> AbsoluteNodeLabel:
        """
        Return the last :py:class:`~.AbsoluteNodeLabel` of
        the :py:class:`~.Context`.

        :raises ContextError: If :py:attr:`labels` is empty.
        """
        if len(self.labels) == 0:
            raise ContextError("Labels are empty. Use `Context.init` to initialize context with labels.")
        last_index = get_last_index(self.labels)
        return self.labels[last_index]

    @property
    def last_response(self) -> Optional[Message]:
        """
        Return the last response of the current :py:class:`~.Context`.
        Return ``None`` if no responses have been added yet.
        """
        if len(self.responses) == 0:
            return None
        last_index = get_last_index(self.responses)
        response = self.responses[last_index]
        return response

    @property
    def last_request(self) -> Message:
        """
        Return the last request of the current :py:class:`~.Context`.

        :raises ContextError: If :py:attr:`responses` is empty.
        """
        if len(self.requests) == 0:
            raise ContextError("No requests have been added.")
        last_index = get_last_index(self.requests)
        return self.requests[last_index]

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
