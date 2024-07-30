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
from typing import List, Optional, Dict, Union

from pydantic import BaseModel, Field, model_validator

from chatsky.core.script_function import BaseResponse, ConstResponse, BaseProcessing
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.transition import Transition

logger = logging.getLogger(__name__)


class Node(BaseModel):
    transitions: List[Transition] = Field(default_factory=list)
    response: Optional[Union[BaseResponse, ConstResponse]] = None
    pre_transition: Dict[str, BaseProcessing] = Field(default_factory=dict)
    pre_response: Dict[str, BaseProcessing] = Field(default_factory=dict)
    misc: dict = Field(default_factory=dict)
    flow: Optional[Flow] = Field(default=None, exclude=True, alias="__flow__")
    name: Optional[str] = Field(default=None, alias="__name__")

    def merge(self, other: Node):
        self.transitions.append(*other.transitions)
        if other.response is not None:
            self.response = other.response
        self.pre_transition.update(**other.pre_transition)
        self.pre_response.update(**other.pre_response)
        self.misc.update(**other.misc)
        return self

    @property
    def inherited_node(self):
        node = Node()

        node.merge(self.flow.script.global_node).merge(self.flow.local_node).merge(self)

        node.flow = self.flow
        node.name = self.name
        return node


class Flow(BaseModel, extra="allow"):
    local_node: Node = Field(alias="local", default_factory=Node)
    __pydantic_extra__: dict[str, Node]
    script: Optional[Script] = Field(default=None, exclude=True, alias="__script__")
    name: Optional[str] = Field(default=None, alias="__name__")

    @model_validator(mode="after")
    def link_nodes(self):
        for name, node in self.__pydantic_extra__.items():
            if node.flow is not None:
                logger.debug(f"Copying node {name!r} -- duplicate of {node.name!r}.")
                copy = node.model_copy()
                node = copy
                self.__pydantic_extra__["name"] = copy
            node.flow = self
            node.name = name
        return self

    def get_node(self, name: str) -> Optional[Node]:
        return self.__pydantic_extra__.get(name)


class Script(BaseModel, extra="allow"):
    global_node: Node = Field(alias="global", default_factory=Node)
    __pydantic_extra__: dict[str, Flow]

    @model_validator(mode="after")
    def link_flows(self):
        for name, flow in self.__pydantic_extra__.items():
            if flow.script is not None:
                logger.debug(f"Copying flow {name!r} -- duplicate of {flow.name!r}.")
                copy = flow.model_copy()
                flow = copy
                self.__pydantic_extra__["name"] = copy
            flow.script = self
            flow.name = name
        return self

    def get_flow(self, name: str) -> Optional[Flow]:
        return self.__pydantic_extra__.get(name)

    def get_node(self, label: AbsoluteNodeLabel) -> Optional[Node]:
        flow = self.get_flow(label.flow_name)
        if flow is None:
            return None
        return flow.get_node(label.node_name)
