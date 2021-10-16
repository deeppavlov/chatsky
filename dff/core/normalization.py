from typing import Dict, List, Tuple
import logging

from typing import Union, Callable, Any


from .keywords import GLOBAL
from .context import Context
from .types import NodeLabel3Type, NodeLabelType, ConditionType

from pydantic import validate_arguments, BaseModel


logger = logging.getLogger(__name__)


Actor = BaseModel


@validate_arguments
def normalize_label(label: NodeLabelType, default_flow_label: str = "") -> Union[Callable, NodeLabel3Type]:
    if isinstance(label, Callable):

        @validate_arguments
        def get_label_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
            try:
                res = label(ctx, actor, *args, **kwargs)
                flow_label, node_label, _ = (str(res[0]), str(res[1]), float(res[2]))
                node = actor.plot.get(flow_label, {}).get(node_label)
                if not node:
                    raise Exception(f"Unknown transitions {res} for {actor.plot}")
            except Exception as exc:
                res = None
                logger.error(f"Exception {exc} of function {label}", exc_info=exc)
            return res

        return get_label_handler  # create wrap to get uniq key for dictionary
    elif isinstance(label, str):
        return (default_flow_label, label, float("-inf"))
    elif isinstance(label, tuple) and len(label) == 2 and isinstance(label[-1], float):
        return (default_flow_label, label[0], label[-1])
    elif isinstance(label, tuple) and len(label) == 2 and isinstance(label[-1], str):
        return (label[0], label[-1], float("-inf"))
    elif isinstance(label, tuple) and len(label) == 3:
        return (label[0], label[1], label[2])


@validate_arguments
def normalize_condition(condition: ConditionType) -> Callable:
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
    transitions = {normalize_label(label): normalize_condition(condition) for label, condition in transitions.items()}
    return transitions


@validate_arguments
def normalize_response(response: Any) -> Callable:
    if isinstance(response, Callable):
        return response
    else:

        @validate_arguments
        def response_handler(ctx: Context, actor: Actor, *args, **kwargs):
            return response

        return response_handler


@validate_arguments
def normalize_processing(processing: Dict[Any, Callable]) -> Callable:
    if isinstance(processing, dict):

        @validate_arguments
        def processing_handler(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
            for processing_name, processing_func in processing.items():
                try:
                    ctx = processing_func(ctx, actor, *args, **kwargs)
                except Exception as exc:
                    logger.error(f"Exception {exc} for {processing_name} and {processing_func}", exc_info=exc)
            return ctx

        return processing_handler


@validate_arguments
def normalize_plot(plot: Dict[str, dict]) -> Dict[str, dict]:
    if isinstance(plot, dict):
        if GLOBAL in plot:
            plot[GLOBAL] = {GLOBAL: plot[GLOBAL]}
        return plot
