import logging

from typing import Union, Callable, Any


from .keywords import GLOBAL, Keywords
from .context import Context
from .types import NodeLabel3Type, NodeLabelType, ConditionType, LabelType

from pydantic import validate_arguments, BaseModel


logger = logging.getLogger(__name__)


Actor = BaseModel


@validate_arguments
def normalize_label(label: NodeLabelType, default_flow_label: LabelType = "") -> Union[Callable, NodeLabel3Type]:
    if isinstance(label, Callable):

        @validate_arguments
        def get_label_handler(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
            try:
                new_label = label(ctx, actor, *args, **kwargs)
                new_label = normalize_label(new_label, default_flow_label)
                flow_label, node_label, _ = new_label
                node = actor.plot.get(flow_label, {}).get(node_label)
                if not node:
                    raise Exception(f"Unknown transitions {new_label} for {actor.plot}")
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
    transitions: dict[NodeLabelType, ConditionType]
) -> dict[Union[Callable, NodeLabel3Type], Callable]:
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
def normalize_processing(processing: dict[Any, Callable]) -> Callable:
    if isinstance(processing, dict):

        @validate_arguments
        def processing_handler(ctx: Context, actor: Actor, *args, **kwargs) -> Context:
            for processing_name, processing_func in processing.items():
                try:
                    ctx = processing_func(ctx, actor, *args, **kwargs)
                except Exception as exc:
                    logger.error(f"Exception {exc} for {processing_name=} and {processing_func=}", exc_info=exc)
            return ctx

        return processing_handler


@validate_arguments
def normalize_plot(
    plot: dict[LabelType, Union[dict[LabelType, dict[Keywords, Any]], dict[Keywords, Any]]]
) -> dict[LabelType, dict[LabelType, dict[str, Any]]]:
    if isinstance(plot, dict):
        if GLOBAL in plot and all([isinstance(item, Keywords) for item in plot[GLOBAL].keys()]):
            plot[GLOBAL] = {GLOBAL: plot[GLOBAL]}
    plot = {
        flow_label: {
            node_label: {key.name.lower(): val for key, val in node.items()} for node_label, node in flow.items()
        }
        for flow_label, flow in plot.items()
    }
    return plot
