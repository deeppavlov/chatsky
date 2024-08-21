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
from uuid import UUID, uuid4
from typing import Any, Optional, Union, Dict, TYPE_CHECKING

from pydantic import BaseModel, Field

from chatsky.core.message import Message, MessageInitTypes
from chatsky.slots.slots import SlotManager
from chatsky.core.node_label import AbsoluteNodeLabel, AbsoluteNodeLabelInitTypes

if TYPE_CHECKING:
    from chatsky.core.script import Node
    from chatsky.core.pipeline import Pipeline
    from chatsky.core.service.types import ComponentExecutionState

logger = logging.getLogger(__name__)


def get_last_index(dictionary: dict) -> int:
    """
    Obtain the last index from the `dictionary`. Return `-1` if the `dict` is empty.

    :param dictionary: Dictionary with unsorted keys.
    :return: Last index from the `dictionary`.
    """
    indices = list(dictionary)
    return max([*indices, -1])


class ContextError(Exception):
    """Raised when context methods are not used correctly."""


class FrameworkData(BaseModel):
    """
    Framework uses this to store data related to any of its modules.
    """

    service_states: Dict[str, ComponentExecutionState] = Field(default_factory=dict, exclude=True)
    "Statuses of all the pipeline services. Cleared at the end of every turn."
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
    `id` is the unique context identifier. By default, randomly generated using `uuid4` `id` is used.
    `id` can be used to trace the user behavior, e.g while collecting the statistical data.
    """
    labels: Dict[int, AbsoluteNodeLabel] = Field(default_factory=dict)
    """
    `labels` stores the history of all passed `labels`

        - key - `id` of the turn.
        - value - `label` on this turn.

    Start label is stored at the ``-1`` key.
    """
    requests: Dict[int, Message] = Field(default_factory=dict)
    """
    `requests` stores the history of all `requests` received by the agent

        - key - `id` of the turn.
        - value - `request` on this turn.
    """
    responses: Dict[int, Message] = Field(default_factory=dict)
    """
    `responses` stores the history of all agent `responses`

        - key - `id` of the turn.
        - value - `response` on this turn.
    """
    misc: Dict[str, Any] = Field(default_factory=dict)
    """
    `misc` stores any custom data. The framework doesn't use this dictionary,
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
        labels = {-1: AbsoluteNodeLabel.model_validate(start_label)}
        if id is None:
            return cls(labels=labels)
        else:
            return cls(labels=labels, id=id)

    def add_request(self, request: MessageInitTypes):
        """
        Add a new `request` to the context.
        The new `request` is added with the index of `last_index + 1`.

        :param request: `request` to be added to the context.
        """
        request_message = Message.model_validate(request)
        last_index = get_last_index(self.requests)
        self.requests[last_index + 1] = request_message

    def add_response(self, response: MessageInitTypes):
        """
        Add a new `response` to the context.
        The new `response` is added with the index of `last_index + 1`.

        :param response: `response` to be added to the context.
        """
        response_message = Message.model_validate(response)
        last_index = get_last_index(self.responses)
        self.responses[last_index + 1] = response_message

    def add_label(self, label: AbsoluteNodeLabelInitTypes):
        """
        Add a new :py:class:`~.AbsoluteNodeLabel` to the context.
        The new `label` is added with the index of `last_index + 1`.

        :param label: `label` that we need to add to the context.
        """
        label = AbsoluteNodeLabel.model_validate(label)
        last_index = get_last_index(self.labels)
        self.labels[last_index + 1] = label

    @property
    def last_label(self) -> AbsoluteNodeLabel:
        """
        Return the last :py:class:`~.AbsoluteNodeLabel` of
        the :py:class:`~.Context`.
        """
        last_index = get_last_index(self.labels)
        label = self.labels.get(last_index)
        if label is None:
            raise ContextError("Labels are empty.")
        return label

    @property
    def last_response(self) -> Optional[Message]:
        """
        Return the last `response` of the current :py:class:`~.Context`.
        Return `None` if `responses` is empty.
        """
        last_index = get_last_index(self.responses)
        return self.responses.get(last_index)

    @property
    def last_request(self) -> Message:
        """
        Return the last `request` of the current :py:class:`~.Context`.
        Return `None` if `requests` is empty.
        """
        last_index = get_last_index(self.requests)
        request = self.requests.get(last_index)
        if request is None:
            raise ContextError("Requests are empty.")
        return request

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
