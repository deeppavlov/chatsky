"""
Normalization
-------------
Normalization module is used to normalize all python objects and functions to a format
that is suitable for script and actor execution process.
This module contains a basic set of functions for normalizing data in a dialog script.
"""

from __future__ import annotations
import logging
from typing import Union, Callable, Optional, TYPE_CHECKING

from .keywords import Keywords
from .context import Context
from .types import NodeLabel3Type, NodeLabelType, ConditionType, LabelType
from .message import Message

if TYPE_CHECKING:
    from dff.pipeline.pipeline.pipeline import Pipeline

logger = logging.getLogger(__name__)


def normalize_label(
    label: NodeLabelType, default_flow_label: LabelType = ""
) -> Union[Callable[[Context, Pipeline], NodeLabel3Type], NodeLabel3Type]:
    """
    The function that is used for normalization of
    :py:const:`default_flow_label <dff.script.NodeLabelType>`.

    :param label: If label is Callable the function is wrapped into try/except
        and normalization is used on the result of the function call with the name label.
    :param default_flow_label: flow_label is used if label does not contain flow_label.
    :return: Result of the label normalization,
        if Callable is returned, the normalized result is returned.
    """
    if callable(label):

        def get_label_handler(ctx: Context, pipeline: Pipeline) -> NodeLabel3Type:
            try:
                new_label = label(ctx, pipeline)
                new_label = normalize_label(new_label, default_flow_label)
                flow_label, node_label, _ = new_label
                node = pipeline.script.get(flow_label, {}).get(node_label)
                if not node:
                    raise Exception(f"Unknown transitions {new_label} for pipeline.script={pipeline.script}")
                if node_label in [Keywords.LOCAL, Keywords.GLOBAL]:
                    raise Exception(f"Invalid transition: can't transition to {flow_label}:{node_label}")
            except Exception as exc:
                new_label = None
                logger.error(f"Exception {exc} of function {label}", exc_info=exc)
            return new_label

        return get_label_handler  # create wrap to get uniq key for dictionary
    elif isinstance(label, str) or isinstance(label, Keywords):
        return (default_flow_label, label, float("-inf"))
    elif isinstance(label, tuple) and len(label) == 2 and isinstance(label[-1], float):
        return (default_flow_label, label[0], label[-1])
    elif isinstance(label, tuple) and len(label) == 2 and isinstance(label[-1], str):
        flow_label = label[0] or default_flow_label
        return (flow_label, label[-1], float("-inf"))
    elif isinstance(label, tuple) and len(label) == 3:
        flow_label = label[0] or default_flow_label
        return (flow_label, label[1], label[2])


def normalize_condition(condition: ConditionType) -> Callable[[Context, Pipeline], bool]:
    """
    The function that is used to normalize `condition`

    :param condition: Condition to normalize.
    :return: The function condition wrapped into the try/except.
    """
    if callable(condition):

        def callable_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
            try:
                return condition(ctx, pipeline)
            except Exception as exc:
                logger.error(f"Exception {exc} of function {condition}", exc_info=exc)
                return False

        return callable_condition_handler


def normalize_response(
    response: Optional[Union[Message, Callable[[Context, "Pipeline"], Message]]]
) -> Callable[[Context, "Pipeline"], Message]:
    """
    This function is used to normalize response. If the response is a Callable, it is returned, otherwise
    the response is wrapped in an asynchronous function and this function is returned.

    :param response: Response to normalize.
    :return: Function that returns callable response.
    """
    if callable(response):
        return response
    else:
        if response is None:
            result = Message()
        elif isinstance(response, Message):
            result = response
        else:
            raise TypeError(type(response))

        async def response_handler(ctx: Context, pipeline: Pipeline):
            return result

        return response_handler
