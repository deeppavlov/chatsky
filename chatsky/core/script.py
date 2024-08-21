"""
Script
------
The Script module provides a set of `pydantic` models for representing the dialog graph.

These models are used by :py:class:`~chatsky.core.service.Actor` to define the conversation flow,
and to determine the appropriate response based on the user's input and the current state of the conversation.
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
    """
    Node is a basic element of the dialog graph.

    Usually used to represent a specific state of a conversation.
    """
    transitions: List[Transition] = Field(default_factory=list)
    """List of transitions possible from this node."""
    response: Optional[AnyResponse] = Field(default=None)
    """Response produced when this node is entered."""
    pre_transition: Dict[str, BaseProcessing] = Field(default_factory=dict)
    """
    A dictionary of :py:class:`.BaseProcessing` functions that are executed before transitions are processed.
    Keys of the dictionary act as names for the processing functions.
    """
    pre_response: Dict[str, BaseProcessing] = Field(default_factory=dict)
    """
    A dictionary of :py:class:`.BaseProcessing` functions that are executed before response is processed.
    Keys of the dictionary act as names for the processing functions.
    """
    misc: dict = Field(default_factory=dict)
    """
    A dictionary that is used to store metadata about the node.
    
    Can be accessed at runtime via :py:attr:`~chatsky.core.context.Context.current_node`.
    """

    def merge(self, other: Node):
        """
        Merge another node into this one:

        - Prepend :py:attr:`transitions` of the other node;
        - Replace response if ``other.response`` is not ``None``;
        - Update :py:attr:`pre_transition`, :py:attr:`pre_response` and :py:attr:`misc` dictionaries.
        """
        self.transitions = [*other.transitions, *self.transitions]
        if other.response is not None:
            self.response = other.response
        self.pre_transition.update(**other.pre_transition)
        self.pre_response.update(**other.pre_response)
        self.misc.update(**other.misc)
        return self


class Flow(BaseModel, extra="allow"):
    """
    Flow is a collection of nodes.
    This is used to group them by a specific purpose.
    """
    local_node: Node = Field(alias="local", default_factory=Node)
    """Node from which all other nodes in this Flow inherit properties according to :py:meth:`Node.merge`."""
    __pydantic_extra__: dict[str, Node]

    @property
    def nodes(self) -> dict[str, Node]:
        """
        A dictionary of all non-local nodes in this flow.

        Keys in the dictionary acts as names for the nodes.
        """
        return self.__pydantic_extra__

    def get_node(self, name: str) -> Optional[Node]:
        """
        Get node with the ``name``.

        :return: Node or ``None`` if it doesn't exist.
        """
        return self.nodes.get(name)


class Script(BaseModel, extra="allow"):
    """
    A script is a collection of nodes.
    It represents an entire dialog graph.
    """
    global_node: Node = Field(alias="global", default_factory=Node)
    """Node from which all other nodes in this Script inherit properties according to :py:meth:`Node.merge`."""
    __pydantic_extra__: dict[str, Flow]

    @property
    def flows(self) -> dict[str, Flow]:
        """
        A dictionary of all flows in this script.

        Keys in the dictionary acts as names for the flows.
        """
        return self.__pydantic_extra__

    def get_flow(self, name: str) -> Optional[Flow]:
        """
        Get flow with the ``name``.

        :return: Flow or ``None`` if it doesn't exist.
        """
        return self.flows.get(name)

    def get_node(self, label: AbsoluteNodeLabel) -> Optional[Node]:
        """
        Get node with the ``label``.

        :return: Node or ``None`` if it doesn't exist.
        """
        flow = self.get_flow(label.flow_name)
        if flow is None:
            return None
        return flow.get_node(label.node_name)

    def get_global_local_inherited_node(self, label: AbsoluteNodeLabel) -> Optional[Node]:
        """
        Return a new node that inherits (using :py:meth:`Node.merge`)
        properties from :py:attr:`Script.global_node`, :py:attr:`Flow.local_node`
        and :py:class`Node`.

        Flow and node are determined by ``label``.

        This is essentially a copy of the node specified by ``label``,
        that inherits properties from `global_node` and `local_node`.

        :return: A new node or ``None`` if it doesn't exist.
        """
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
