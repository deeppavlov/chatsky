"""
Script
---------------------------
Here is a set of `pydantic` models for the dialog graph.
"""
# %%

import logging
from typing import Callable, Optional, Any, Dict, Union

from pydantic import BaseModel, validator, Extra

from .types import LabelType, NodeLabelType, ConditionType
from .message import Message
from .normalization import normalize_response, normalize_processing, normalize_transitions, normalize_script
from typing import ForwardRef

logger = logging.getLogger(__name__)


Actor = ForwardRef("Actor")
Context = ForwardRef("Context")


class Node(BaseModel, extra=Extra.forbid):
    """
    The class for the `Node` object.
    """

    transitions: Dict[NodeLabelType, ConditionType] = {}
    response: Optional[Union[Message, Callable[[Context, Actor], Message]]] = None
    pre_transitions_processing: Dict[Any, Callable] = {}
    pre_response_processing: Dict[Any, Callable] = {}
    misc: dict = {}

    _normalize_transitions = validator("transitions", allow_reuse=True)(normalize_transitions)

    def run_response(self, ctx: Context, actor: Actor, *args, **kwargs) -> Context:
        """
        Executes the normalized response.
        See details in the :py:func:`~normalize_response` function of `normalization.py`.
        """
        response = normalize_response(self.response)
        return response(ctx, actor, *args, **kwargs)

    def run_pre_response_processing(self, ctx: Context, actor: Actor, *args, **kwargs) -> Context:
        """
        Executes pre-processing of responses.
        """
        return self.run_processing(self.pre_response_processing, ctx, actor, *args, **kwargs)

    def run_pre_transitions_processing(self, ctx: Context, actor: Actor, *args, **kwargs) -> Context:
        """
        Executes pre-processing of transitions.
        """
        return self.run_processing(self.pre_transitions_processing, ctx, actor, *args, **kwargs)

    def run_processing(self, processing: Dict[Any, Callable], ctx: Context, actor: Actor, *args, **kwargs) -> Context:
        """
        Executes the normalized processing.
        See details in the :py:func:`~normalize_processing` function of `normalization.py`.
        """
        processing = normalize_processing(processing)
        return processing(ctx, actor, *args, **kwargs)


class Script(BaseModel, extra=Extra.forbid):
    """
    The class for the `Script` object.
    """

    script: Dict[LabelType, Dict[LabelType, Node]]

    _normalize_script = validator("script", allow_reuse=True, pre=True)(normalize_script)

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
