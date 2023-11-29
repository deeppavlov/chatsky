"""
Script
------
The Script module provides a set of `pydantic` models for representing the dialog graph.
These models are used to define the conversation flow, and to determine the appropriate response based on
the user's input and the current state of the conversation.
"""
# %%

import logging
from typing import Callable, Optional, Any, Dict, Union

from pydantic import BaseModel, field_validator

from .types import LabelType, NodeLabelType, ConditionType, NodeLabel3Type
from .message import Message
from .keywords import Keywords
from .normalization import normalize_response, normalize_processing, normalize_condition, normalize_label, validate_call
from typing import ForwardRef

logger = logging.getLogger(__name__)


Pipeline = ForwardRef("Pipeline")
Context = ForwardRef("Context")


class Node(BaseModel, extra="forbid"):
    """
    The class for the `Node` object.
    """

    transitions: Dict[NodeLabelType, ConditionType] = {}
    response: Optional[Union[Message, Callable[[Context, Pipeline], Message]]] = None
    pre_transitions_processing: Dict[Any, Callable] = {}
    pre_response_processing: Dict[Any, Callable] = {}
    misc: dict = {}

    @field_validator("transitions", mode="before")
    @classmethod
    @validate_call
    def normalize_transitions(
        cls, transitions: Dict[NodeLabelType, ConditionType]
    ) -> Dict[Union[Callable, NodeLabel3Type], Callable]:
        """
        The function which is used to normalize transitions and returns normalized dict.

        :param transitions: Transitions to normalize.
        :return: Transitions with normalized label and condition.
        """
        transitions = {
            normalize_label(label): normalize_condition(condition) for label, condition in transitions.items()
        }
        return transitions

    def run_response(self, ctx: Context, pipeline: Pipeline, *args, **kwargs) -> Context:
        """
        Executes the normalized response.
        See details in the :py:func:`~normalize_response` function of `normalization.py`.
        """
        response = normalize_response(self.response)
        return response(ctx, pipeline, *args, **kwargs)

    def run_pre_response_processing(self, ctx: Context, pipeline: Pipeline, *args, **kwargs) -> Context:
        """
        Executes pre-processing of responses.
        """
        return self.run_processing(self.pre_response_processing, ctx, pipeline, *args, **kwargs)

    def run_pre_transitions_processing(self, ctx: Context, pipeline: Pipeline, *args, **kwargs) -> Context:
        """
        Executes pre-processing of transitions.
        """
        return self.run_processing(self.pre_transitions_processing, ctx, pipeline, *args, **kwargs)

    def run_processing(
        self, processing: Dict[Any, Callable], ctx: Context, pipeline: Pipeline, *args, **kwargs
    ) -> Context:
        """
        Executes the normalized processing.
        See details in the :py:func:`~normalize_processing` function of `normalization.py`.
        """
        processing = normalize_processing(processing)
        return processing(ctx, pipeline, *args, **kwargs)


class Script(BaseModel, extra="forbid"):
    """
    The class for the `Script` object.
    """

    script: Dict[LabelType, Dict[LabelType, Node]]

    @field_validator("script", mode="before")
    @classmethod
    @validate_call
    def normalize_script(cls, script: Dict[LabelType, Any]) -> Dict[LabelType, Dict[LabelType, Dict[str, Any]]]:
        """
        This function normalizes :py:class:`.Script`: it returns dict where the GLOBAL node is moved
        into the flow with the GLOBAL name. The function returns the structure

        `{GLOBAL: {...NODE...}, ...}` -> `{GLOBAL: {GLOBAL: {...NODE...}}, ...}`.

        :param script: :py:class:`.Script` that describes the dialog scenario.
        :return: Normalized :py:class:`.Script`.
        """
        if isinstance(script, dict):
            if Keywords.GLOBAL in script and all(
                [isinstance(item, Keywords) for item in script[Keywords.GLOBAL].keys()]
            ):
                script[Keywords.GLOBAL] = {Keywords.GLOBAL: script[Keywords.GLOBAL]}
        return script

    def __getitem__(self, key):
        return self.script[key]

    def get(self, key, value=None):
        return self.script.get(key, value)

    def keys(self):
        return self.script.keys()

    def items(self):
        return self.script.items()

    def values(self):
        return self.script.values()

    def __iter__(self):
        return self.script.__iter__()
