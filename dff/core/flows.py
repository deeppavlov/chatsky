# %%
import logging
import random
from typing import Union, Callable, Pattern, Optional

from pydantic import BaseModel, conlist, validator, validate_arguments

from context import Context

logger = logging.getLogger(__name__)

CONDITION_DEPTH_TYPE_CHECKING = 20
# Callable = str
# Pattern = str

NodeLabelTupledType = Union[
    tuple[str, float],
    tuple[str, str],
    tuple[str, str, float],
]
NodeLabelType = Union[Callable, NodeLabelTupledType, str]
ConditionType = Union[Callable, Pattern, str]
for _ in range(CONDITION_DEPTH_TYPE_CHECKING):
    ConditionType = Union[conlist(ConditionType, min_items=1), Callable, Pattern, str]


@validate_arguments
def normalize_node_label(
    node_label: NodeLabelType, flow_label: str, default_priority: float
) -> Union[Callable, tuple[str, str, float]]:
    if isinstance(node_label, Callable):

        @validate_arguments
        def get_node_label_handler(ctx: Context, flows: Flows, *args, **kwargs) -> tuple[str, str, float]:
            try:
                res = node_label(ctx, flows, *args, **kwargs)
                res = (str(res[0]), str(res[1]), float(res[2]))
                node = flows.get_node(res)
                if not node:
                    raise Exception(f"Unknown transitions {res} {flows}")
            except Exception as exc:
                res = None
                logger.error(f"Exception {exc} of function {node_label}", exc_info=exc)
            return res

        return get_node_label_handler  # create wrap to get uniq key for dictionary
    elif isinstance(node_label, str):
        return (flow_label, node_label, default_priority)
    elif isinstance(node_label, tuple) and len(node_label) == 2 and isinstance(node_label[-1], float):
        return (flow_label, node_label[0], node_label[-1])
    elif isinstance(node_label, tuple) and len(node_label) == 2 and isinstance(node_label[-1], str):
        return (node_label[0], node_label[-1], default_priority)
    elif isinstance(node_label, tuple) and len(node_label) == 3:
        return (node_label[0], node_label[1], node_label[2])
    raise NotImplementedError(f"Unexpected node label {node_label}")


@validate_arguments
def normalize_conditions(conditions: ConditionType, reduce_function=any) -> Callable:
    if isinstance(conditions, Callable):
        # TODO: add try/exc
        return conditions
    elif isinstance(conditions, Pattern):

        @validate_arguments
        def regexp_condition_handler(ctx: Context, flows: Flows, *args, **kwargs) -> bool:
            human_text, annotations = ctx.current_human_annotated_utterance
            return bool(conditions.search(human_text))

        return regexp_condition_handler
    elif isinstance(conditions, str):

        @validate_arguments
        def str_condition_handler(ctx: Context, flows: Flows, *args, **kwargs) -> bool:
            human_text, annotations = ctx.current_human_annotated_utterance
            return conditions in human_text

        return str_condition_handler
    elif isinstance(conditions, list):

        function_expression_indexes = [
            index
            for index, (func, args) in enumerate(zip(conditions, conditions[1:]))
            if func in [any, all] and (isinstance(args, list) or isinstance(args, tuple))
        ]
        if function_expression_indexes:

            def reduce_func(ctx: Context, flows: Flows, *args, **kwargs) -> bool:
                # function closure
                local_conditions = conditions[:]
                local_function_expression_indexes = function_expression_indexes[:]
                local_reduce_function = reduce_function

                # apply reduced functions
                reduced_bools = []
                for start_func_index in local_function_expression_indexes:
                    # get sub conditions
                    sub_reduce_function = local_conditions[start_func_index]
                    sub_conditions = local_conditions[start_func_index + 1]
                    # drop reduced items of local_conditions
                    local_conditions[start_func_index : start_func_index + 2] = []

                    normalized_condition = normalize_conditions(sub_conditions, sub_reduce_function)
                    reduced_bools += [normalized_condition(ctx, flows, *args, **kwargs)]
                unreduced_conditions = [normalize_conditions(cond) for cond in local_conditions]
                # apply unreduced functions
                unreduced_bools = [cond(ctx, flows, *args, **kwargs) for cond in unreduced_conditions]

                bools = unreduced_bools + reduced_bools
                return local_reduce_function(bools)

            return reduce_func
        else:

            @validate_arguments
            def iterable_condition_handler(ctx: Context, flows: Flows, *args, **kwargs) -> bool:
                bools = [normalize_conditions(cond)(ctx, flows, *args, **kwargs) for cond in conditions]
                return reduce_function(bools)

            return iterable_condition_handler
    raise NotImplementedError(f"Unexpected conditions {conditions}")


@validate_arguments
def normalize_response(response: Union[conlist(str, min_items=1), str, Callable]) -> Callable:
    if isinstance(response, Callable):
        return response
    elif isinstance(response, str):

        @validate_arguments
        def str_response_handler(ctx: Context, flows: Flows, *args, **kwargs):
            return response

        return str_response_handler
    elif isinstance(response, list):

        @validate_arguments
        def list_response_handler(ctx: Context, flows: Flows, *args, **kwargs):
            return random.choice(response)

        return list_response_handler
    raise NotImplementedError(f"Unexpected response {response}")


# TODO: add exeption handling for processing
@validate_arguments
def normalize_processing(processing: Optional[Union[Callable, conlist(Callable, min_items=1)]]) -> Callable:
    if isinstance(processing, Callable):
        return processing
    elif isinstance(processing, list):

        @validate_arguments
        def list_processing_handler(
            flow_label: str, node: Node, ctx: Context, flows: Flows, *args, **kwargs
        ) -> Optional[tuple[str, Node]]:
            for proc in processing:
                flow_label, node = proc(flow_label, node, ctx, flows, *args, **kwargs)
            return flow_label, node

        return list_processing_handler
    elif processing is None:

        @validate_arguments
        def none_handler(
            flow_label: str, node: Node, ctx: Context, flows: Flows, *args, **kwargs
        ) -> Optional[tuple[str, Node]]:
            return flow_label, node

        return none_handler
    raise NotImplementedError(f"Unexpected processing {processing}")


class Transition(BaseModel):
    global_transitions: dict[NodeLabelType, ConditionType] = {}
    transitions: dict[NodeLabelType, ConditionType] = {}

    @validate_arguments
    def get_transitions(
        self, flow_label: str, default_priority: float, global_transition_flag=False
    ) -> dict[Union[Callable, tuple[str, str, float]], Callable]:
        transitions = {}
        items = self.global_transitions if global_transition_flag else self.transitions
        for node_label in items:
            normalized_node_label = normalize_node_label(node_label, flow_label, default_priority)
            normalized_conditions = normalize_conditions(items[node_label])
            transitions[normalized_node_label] = normalized_conditions
        return transitions


class Node(Transition):
    response: Union[conlist(str, min_items=1), str, Callable]
    processing: Union[Callable, conlist(Callable, min_items=1)] = None

    def get_response(self):
        return normalize_response(self.response)

    def get_processing(self):
        return normalize_processing(self.processing)


class Flow(Transition):
    graph: dict[str, Node] = {}

    @validate_arguments
    def get_transitions(
        self, flow_label: str, default_priority: float, global_transition_flag=False
    ) -> dict[Union[Callable, tuple[str, str, float]], Callable]:
        transitions = super(Flow, self).get_transitions(flow_label, default_priority, global_transition_flag)
        for node in self.graph.values():
            transitions |= node.get_transitions(flow_label, default_priority, global_transition_flag)
        return transitions


def error_handler(error_msgs: list, msg: str, exception: Optional[Exception] = None, logging_flag: bool = True):
    error_msgs.append(msg)
    logging_flag and logger.error(msg, exc_info=exception)


class Flows(BaseModel):
    flows: dict[str, Flow]

    @validator("flows")
    def is_not_empty(cls, fields: dict) -> dict:
        if not any(fields.values()):
            raise ValueError("expected not empty flows")
        return fields

    @validate_arguments
    def validate_flows(
        self,
        response_validation_flag: Optional[bool] = None,
        logging_flag: bool = True,
    ):
        transitions = self.get_transitions(-1, False) | self.get_transitions(-1, True)
        error_msgs = []
        for callable_node_label, condition in transitions.items():
            ctx = Context()
            ctx.add_human_utterance("text")
            flows = self.copy(deep=True)
            node_label = (
                callable_node_label(ctx, flows) if isinstance(callable_node_label, Callable) else callable_node_label
            )

            # validate node_label
            try:
                node = self.get_node(node_label)
            except Exception as exc:
                node = None
                msg = f"Got exception '''{exc}''' for {callable_node_label=}"
                error_handler(error_msgs, msg, exc, logging_flag)

            if not isinstance(node, Node):
                msg = f"Could not find node with node_label={node_label[:2]}"
                error_handler(error_msgs, msg, None, logging_flag)
                continue

            # validate response
            if response_validation_flag or response_validation_flag is None:
                response_func = normalize_response(node.response)
                n_errors = len(error_msgs)
                try:
                    response_result = response_func(ctx, flows)
                    if not isinstance(response_result, str):
                        msg = (
                            f"Expected type of response_result needed str but got {type(response_result)=}"
                            f" for node_label={node_label[:2]}"
                        )
                        error_handler(error_msgs, msg, None, logging_flag)
                except Exception as exc:
                    msg = (
                        f"Got exception '''{exc}''' during response execution "
                        f"for {node_label=} and {node.response=}"
                    )
                    error_handler(error_msgs, msg, exc, logging_flag)
                if n_errors != len(error_msgs) and response_validation_flag is None:
                    logger.info(
                        "response_validation_flag was not setuped, by default responses validation is enabled. "
                        "It's service message can be switched off by manually setting response_validation_flag"
                    )

            # validate condition
            try:
                bool(condition(ctx, flows))
            except Exception as exc:
                msg = f"Got exception '''{exc}''' during condition execution for {node_label=}"
                error_handler(error_msgs, msg, exc, logging_flag)
        return error_msgs

    @validate_arguments
    def get_transitions(
        self, default_priority: float, global_transition_flag=False
    ) -> dict[Union[Callable, tuple[str, str, float]], Callable]:
        transitions = {}
        for flow_label, node in self.flows.items():
            transitions |= node.get_transitions(flow_label, default_priority, global_transition_flag)
        return transitions

    @validate_arguments
    def get_node(self, node_label: NodeLabelType, flow_label: str = "") -> Optional[Node]:
        normalized_node_label = normalize_node_label(node_label, flow_label, -1)
        flow_label = normalized_node_label[0]
        node_label = normalized_node_label[1]
        node = self.flows.get(flow_label, Flow()).graph.get(node_label)
        if node is None:
            logger.warn(f"Unknown pair(flow_label:node_label) = {flow_label}:{node_label}")
        return node


# from pydantic.schema import schema
# open("schema_markup.json", "wt").write(Flows.schema_json())
