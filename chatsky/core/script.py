"""
Script
------
The Script module provides a set of `pydantic` models for representing the dialog graph.
These models are used to define the conversation flow, and to determine the appropriate response based on
the user's input and the current state of the conversation.
"""

# %%
from __future__ import annotations
import logging
from typing import List, Optional, Dict

from pydantic import BaseModel, Field

from chatsky.core.script_function import AnyResponse, BaseProcessing
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.transition import Transition

logger = logging.getLogger(__name__)


class Node(BaseModel):
    transitions: List[Transition] = Field(default_factory=list)
    response: Optional[AnyResponse] = Field(default=None)
    pre_transition: Dict[str, BaseProcessing] = Field(default_factory=dict)
    pre_response: Dict[str, BaseProcessing] = Field(default_factory=dict)
    misc: dict = Field(default_factory=dict)

    def merge(self, other: Node):
        self.transitions.extend(other.transitions)
        if other.response is not None:
            self.response = other.response
        self.pre_transition.update(**other.pre_transition)
        self.pre_response.update(**other.pre_response)
        self.misc.update(**other.misc)
        return self


class Flow(BaseModel, extra="allow"):
    local_node: Node = Field(alias="local", default_factory=Node)
    __pydantic_extra__: dict[str, Node]

    @property
    def nodes(self) -> dict[str, Node]:
        return self.__pydantic_extra__

    def get_node(self, name: str) -> Optional[Node]:
        return self.nodes.get(name)


class Script(BaseModel, extra="allow"):
    global_node: Node = Field(alias="global", default_factory=Node)
    __pydantic_extra__: dict[str, Flow]

    @property
    def flows(self) -> dict[str, Flow]:
        return self.__pydantic_extra__

    def get_flow(self, name: str) -> Optional[Flow]:
        return self.flows.get(name)

    def get_node(self, label: AbsoluteNodeLabel) -> Optional[Node]:
        flow = self.get_flow(label.flow_name)
        if flow is None:
            return None
        return flow.get_node(label.node_name)

    def get_global_local_inherited_node(self, label: AbsoluteNodeLabel) -> Optional[Node]:
        flow = self.get_flow(label.flow_name)
        if flow is None:
            return None
        node = flow.get_node(label.node_name)
        if node is None:
            return None

        inheritant_node = Node()

        return inheritant_node.merge(self.global_node).merge(flow.local_node).merge(node)


GLOBAL = "global"
"""Key for :py:attr:`~chatsky.core.script.Script.global_node`."""
LOCAL = "local"
"""Key for :py:attr:`~chatsky.core.script.Flow.local_node`."""
TRANSITIONS = "transitions"
"""Key for :py:attr:`~chatsky.core.script.Node.transitions`."""
RESPONSE = "response"
"""Key for :py:attr:`~chatsky.core.script.Node.response`."""
MISC = "misc"
"""Key for :py:attr:`~chatsky.core.script.Node.misc`."""
PRE_RESPONSE = "pre_response"
"""Key for :py:attr:`~chatsky.core.script.Node.pre_response`."""
PRE_TRANSITION = "pre_transition"
"""Key for :py:attr:`~chatsky.core.script.Node.pre_transition`."""
