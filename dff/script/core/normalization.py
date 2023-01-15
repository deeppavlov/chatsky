"""
Normalization
---------------------------
A basic set of functions for normalizing data in a dialog script is placed here.
"""
import logging

from typing import Union, Callable, Any, Dict, Optional

from .keywords import GLOBAL, Keywords
from .context import Context
from .types import NodeLabel3Type, NodeLabelType, ConditionType, LabelType
from .message import Message

from pydantic import validate_arguments, BaseModel

logger = logging.getLogger(__name__)

Actor = BaseModel


@validate_arguments
def normalize_label(label: NodeLabelType, default_flow_label: LabelType = "") -> Union[Callable, NodeLabel3Type]:
    """
    The function that is used for normalization of
    :py:const:`default_flow_label <dff.script.NodeLabelType>`.

    :param label: If `label` is `Callable` the function is wrapped into try/except
        and normalization is used on the result of the function call with the name `label`.
    :param default_flow_label: `flow_label` is used if `label` does not contain `flow_label`.

    :return: Result of the `label` normalization,
        if `Callable` is returned, the normalized result is returned.
    """
    if isinstance(label, Callable):

        @validate_arguments
        def get_label_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
            try:
                new_label = label(ctx, actor, *args, **kwargs)
                new_label = normalize_label(new_label, default_flow_label)
                flow_label, node_label, _ = new_label
                node = actor.script.get(flow_label, {}).get(node_label)
                if not node:
                    raise Exception(f"Unknown transitions {new_label} for actor.script={actor.script}")
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


@validate_arguments
def normalize_condition(condition: ConditionType) -> Callable:
    """
    The functon that is used to normalize `condition`

    :param condition: `condition` to normalize.
    :return: The function `condition` wrapped into the try/except.
    """
    if isinstance(condition, Callable):

        @validate_arguments
        def callable_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
            try:
                return condition(ctx, actor, *args, **kwargs)
            except Exception as exc:
                logger.error(f"Exception {exc} of function {condition}", exc_info=exc)
                return False

        return callable_condition_handler


@validate_arguments
def normalize_transitions(
    transitions: Dict[NodeLabelType, ConditionType]
) -> Dict[Union[Callable, NodeLabel3Type], Callable]:
    """
    The function which is used to normalize `transitions` and returns normalized `dict`.

    :param transitions: `transitions` to normalize.
    :return: `transitions` with normalized `label` and `condition`.
    """
    transitions = {normalize_label(label): normalize_condition(condition) for label, condition in transitions.items()}
    return transitions


@validate_arguments
def normalize_response(response: Optional[Union[Message, Callable[..., Message]]]) -> Callable[..., Message]:
    """
    This function is used to normalize `response`, if `response` Callable, it is returned, otherwise
    `response` is wrapped to the function and this function is returned.

    :param response: `response` to normalize.
    :return: Function that returns callable response.
    """
    if isinstance(response, Callable):
        return response
    else:
        if response is None:
            result = Message()
        elif isinstance(response, Message):
            result = response
        else:
            raise TypeError(type(response))

        @validate_arguments
        def response_handler(ctx: Context, actor: Actor, *args, **kwargs):
            return result

        return response_handler


@validate_arguments
def normalize_processing(processing: Dict[Any, Callable]) -> Callable:
    """
    This function is used to normalize `processing`.
    It returns function that consecutively applies all preprocessing stages from `dict`.

    :param processing: `processing` which contains all preprocessing stages in a format "PROC_i" -> proc_func_i.
    :return: Function that consequentially applies all preprocessing stages from `dict`.
    """
    if isinstance(processing, dict):

        @validate_arguments
        def processing_handler(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
            for processing_name, processing_func in processing.items():
                try:
                    if processing_func is not None:
                        ctx = processing_func(ctx, actor, *args, **kwargs)
                except Exception as exc:
                    logger.error(
                        f"Exception {exc} for processing_name={processing_name} and processing_func={processing_func}",
                        exc_info=exc,
                    )
            return ctx

        return processing_handler


@validate_arguments
def map_deprecated_key(key: str) -> str:
    """
    This function is used to map deprecated keyword to new one.

    :param key: A keyword of a node.
    :return: A mapped keyword of a node.
    """
    if key == "processing":
        logger.warning(
            "Use the new key 'PRE_RESPONSE_PROCESSING instead of the deprecated key 'PROCESSING',"
            " which will be removed in future versions."
        )
        return "pre_response_processing"
    return key


@validate_arguments
def normalize_keywords(
    script: Dict[LabelType, Dict[LabelType, Dict[Keywords, Any]]]
) -> Dict[LabelType, Dict[LabelType, Dict[str, Any]]]:
    """
    This function is used to normalize keywords in the script.

    :param script: `Script`, containing all transitions between states based in the keywords.
    :return: `Script` with the normalized keywords.
    """

    script = {
        flow_label: {
            node_label: {map_deprecated_key(key.name.lower()): val for key, val in node.items()}
            for node_label, node in flow.items()
        }
        for flow_label, flow in script.items()
    }
    return script


@validate_arguments
def normalize_script(script: Dict[LabelType, Any]) -> Dict[LabelType, Dict[LabelType, Dict[str, Any]]]:
    """
    This function normalizes `Script`: it returns `dict` where the `GLOBAL` node is moved
    into the flow with the `GLOBAL` name. The function returns the structure

    `{GLOBAL: {...NODE...}, ...}` -> `{GLOBAL: {GLOBAL: {...NODE...}}, ...}`.

    :param script: `Script` that describes the dialog scenario.
    :return: Normalized `Script`.
    """
    if isinstance(script, dict):
        if GLOBAL in script and all([isinstance(item, Keywords) for item in script[GLOBAL].keys()]):
            script[GLOBAL] = {GLOBAL: script[GLOBAL]}
    return normalize_keywords(script)
