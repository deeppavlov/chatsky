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

from pydantic import BaseModel, Field, AliasChoices

from chatsky.core.script_function import AnyResponse, BaseProcessing
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.transition import Transition

logger = logging.getLogger(__name__)


class Node(BaseModel, extra="forbid"):
    """
    Node is a basic element of the dialog graph.

    Usually used to represent a specific state of a conversation.
    """

    transitions: List[Transition] = Field(
        validation_alias=AliasChoices("transitions", "TRANSITIONS"), default_factory=list
    )
    """List of transitions possible from this node."""
    response: Optional[AnyResponse] = Field(validation_alias=AliasChoices("response", "RESPONSE"), default=None)
    """Response produced when this node is entered."""
    pre_transition: Dict[str, BaseProcessing] = Field(
        validation_alias=AliasChoices("pre_transition", "PRE_TRANSITION"), default_factory=dict
    )
    """
    A dictionary of :py:class:`.BaseProcessing` functions that are executed before transitions are processed.
    Keys of the dictionary act as names for the processing functions.
    """
    pre_response: Dict[str, BaseProcessing] = Field(
        validation_alias=AliasChoices("pre_response", "PRE_RESPONSE"), default_factory=dict
    )
    """
    A dictionary of :py:class:`.BaseProcessing` functions that are executed before response is processed.
    Keys of the dictionary act as names for the processing functions.
    """
    misc: dict = Field(validation_alias=AliasChoices("misc", "MISC"), default_factory=dict)
    """
    A dictionary that is used to store metadata about the node.

    Can be accessed at runtime via :py:attr:`~chatsky.core.context.Context.current_node`.
    """

    def inherit_from_other(self, other: Node):
        """
        Inherit properties from another node into this one:

        - Extend ``self.transitions`` with :py:attr:`transitions` of the other node;
        - Replace response with ``other.response`` if ``self.response`` is ``None``;
        - Dictionaries (:py:attr:`pre_transition`, :py:attr:`pre_response` and :py:attr:`misc`)
          are appended to this node's dictionaries except for the repeating keys.
          For example, ``inherit_from_other({1: 1, 3: 3}, {1: 0, 2: 2}) == {1: 1, 3: 3, 2: 2}``.

        Basically, only non-conflicting properties of ``other`` are inherited.
        """

        def merge_dicts(first: dict, second: dict):
            first.update({k: v for k, v in second.items() if k not in first})

        self.transitions.extend(other.transitions)
        if self.response is None:
            self.response = other.response
        merge_dicts(self.pre_transition, other.pre_transition)
        merge_dicts(self.pre_response, other.pre_response)
        merge_dicts(self.misc, other.misc)
        return self


class Flow(BaseModel, extra="allow"):
    """
    Flow is a collection of nodes.
    This is used to group them by a specific purpose.
    """

    local_node: Node = Field(
        validation_alias=AliasChoices("local", "LOCAL", "local_node", "LOCAL_NODE"), default_factory=Node
    )
    """
    Node from which all other nodes in this Flow inherit properties
    according to :py:meth:`Node.inherit_from_other`.
    """
    __pydantic_extra__: Dict[str, Node]

    @property
    def nodes(self) -> Dict[str, Node]:
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

    global_node: Node = Field(
        validation_alias=AliasChoices("global", "GLOBAL", "global_node", "GLOBAL_NODE"), default_factory=Node
    )
    """
    Node from which all other nodes in this Script inherit properties
    according to :py:meth:`Node.inherit_from_other`.
    """
    __pydantic_extra__: Dict[str, Flow]

    @property
    def flows(self) -> Dict[str, Flow]:
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

    def get_inherited_node(self, label: AbsoluteNodeLabel) -> Optional[Node]:
        """
        Return a new node that inherits (using :py:meth:`Node.inherit_from_other`)
        properties from :py:class:`Node`, :py:attr:`Flow.local_node`
        and :py:attr:`Script.global_node` (in that order).

        Flow and node are determined by ``label``.

        This is essentially a copy of the node specified by ``label``,
        that inherits properties from ``local_node`` and ``global_node``.

        :return: A new node or ``None`` if it doesn't exist.
        """
        flow = self.get_flow(label.flow_name)
        if flow is None:
            return None
        node = flow.get_node(label.node_name)
        if node is None:
            return None

        inheritant_node = Node()

        return (
            inheritant_node.inherit_from_other(node)
            .inherit_from_other(flow.local_node)
            .inherit_from_other(self.global_node)
        )


GLOBAL = "GLOBAL"
"""Key for :py:attr:`~chatsky.core.script.Script.global_node`."""
LOCAL = "LOCAL"
"""Key for :py:attr:`~chatsky.core.script.Flow.local_node`."""
TRANSITIONS = "TRANSITIONS"
"""Key for :py:attr:`~chatsky.core.script.Node.transitions`."""
RESPONSE = "RESPONSE"
"""Key for :py:attr:`~chatsky.core.script.Node.response`."""
MISC = "MISC"
"""Key for :py:attr:`~chatsky.core.script.Node.misc`."""
PRE_RESPONSE = "PRE_RESPONSE"
"""Key for :py:attr:`~chatsky.core.script.Node.pre_response`."""
PRE_TRANSITION = "PRE_TRANSITION"
"""Key for :py:attr:`~chatsky.core.script.Node.pre_transition`."""
