import logging
import random
from typing import Union, Callable, Pattern, Optional, Any


from dff.core.context import Context
from dff.core.condition_handlers import deep_copy_condition_handler

from pydantic import BaseModel, conlist, validator, validate_arguments, Extra


logger = logging.getLogger(__name__)
# TODO: add texts

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
        def get_node_label_handler(ctx: Context, actor: Actor, *args, **kwargs) -> tuple[str, str, float]:
            try:
                res = node_label(ctx, actor, *args, **kwargs)
                res = (str(res[0]), str(res[1]), float(res[2]))
                node = actor.flows.get_node(res)
                if not node:
                    raise Exception(f"Unknown transitions {res} {actor.flows}")
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
        def regexp_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
            human_text, annotations = ctx.current_human_annotated_utterance
            return bool(conditions.search(human_text))

        return regexp_condition_handler
    elif isinstance(conditions, str):

        @validate_arguments
        def str_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
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

            def reduce_func(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
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
                    reduced_bools += [normalized_condition(ctx, actor, *args, **kwargs)]
                unreduced_conditions = [normalize_conditions(cond) for cond in local_conditions]
                # apply unreduced functions
                unreduced_bools = [cond(ctx, actor, *args, **kwargs) for cond in unreduced_conditions]

                bools = unreduced_bools + reduced_bools
                return local_reduce_function(bools)

            return reduce_func
        else:

            @validate_arguments
            def iterable_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
                bools = [normalize_conditions(cond)(ctx, actor, *args, **kwargs) for cond in conditions]
                return reduce_function(bools)

            return iterable_condition_handler
    raise NotImplementedError(f"Unexpected conditions {conditions}")


@validate_arguments
def normalize_response(response: Union[conlist(str, min_items=1), str, Callable]) -> Callable:
    if isinstance(response, Callable):
        return response
    elif isinstance(response, str):

        @validate_arguments
        def str_response_handler(ctx: Context, actor: Actor, *args, **kwargs):
            return response

        return str_response_handler
    elif isinstance(response, list):

        @validate_arguments
        def list_response_handler(ctx: Context, actor: Actor, *args, **kwargs):
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
            node_label: NodeLabelTupledType, node: Node, ctx: Context, actor: Actor, *args, **kwargs
        ) -> Optional[tuple[str, Node]]:
            for proc in processing:
                node_label, node = proc(node_label, node, ctx, actor, *args, **kwargs)
            return node_label, node

        return list_processing_handler
    elif processing is None:

        @validate_arguments
        def none_handler(
            node_label: NodeLabelTupledType, node: Node, ctx: Context, actor: Actor, *args, **kwargs
        ) -> Optional[tuple[str, Node]]:
            return node_label, node

        return none_handler
    raise NotImplementedError(f"Unexpected processing {processing}")


class Transition(BaseModel, extra=Extra.forbid):
    @validate_arguments
    def get_transitions(
        self, flow_label: str, default_priority: float, global_transition_flag=False
    ) -> dict[Union[Callable, tuple[str, str, float]], Callable]:
        transitions = {}
        gtrs = self.global_transitions if hasattr(self, "global_transitions") else {}
        trs = self.transitions if hasattr(self, "transitions") else {}
        items = gtrs if global_transition_flag else trs
        for node_label in items:
            normalized_node_label = normalize_node_label(node_label, flow_label, default_priority)
            normalized_conditions = normalize_conditions(items[node_label])
            transitions[normalized_node_label] = normalized_conditions
        return transitions


class Node(Transition):
    transitions: dict[NodeLabelType, ConditionType] = {}
    response: Union[conlist(str, min_items=1), str, Callable]
    processing: Union[Callable, conlist(Callable, min_items=1)] = None
    misc: Optional[Any] = None

    def get_response(self):
        return normalize_response(self.response)

    def get_processing(self):
        return normalize_processing(self.processing)


class Flow(Transition):
    global_transitions: dict[NodeLabelType, ConditionType] = {}
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


class Flows(BaseModel, extra=Extra.forbid):
    flows: dict[str, Flow]

    @validator("flows")
    def is_not_empty(cls, fields: dict) -> dict:
        if not any(fields.values()):
            raise ValueError("expected not empty flows")
        return fields

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

    def __getitem__(self, k):
        return self.flows[k]

    def get(self, k, item=None):
        return self.flows.get(k, item)

    def keys(self):
        return self.flows.keys()

    def items(self):
        return self.flows.items()

    def values(self):
        return self.flows.values()

    def __iter__(self):
        return self.flows


class Actor(BaseModel):
    flows: Union[Flows, dict]
    start_node_label: tuple[str, str, float]
    fallback_node_label: Optional[tuple[str, str, float]] = None
    default_priority: float = 1.0
    response_validation_flag: Optional[bool] = None
    validation_logging_flag: bool = True
    pre_handlers: list[Callable] = []
    post_handlers: list[Callable] = []

    @validate_arguments
    def __init__(
        self,
        flows: Union[Flows, dict],
        start_node_label: tuple[str, str],
        fallback_node_label: Optional[tuple[str, str]] = None,
        default_priority: float = 1.0,
        response_validation_flag: Optional[bool] = None,
        validation_logging_flag: bool = True,
        pre_handlers: list[Callable] = [],
        post_handlers: list[Callable] = [],
        *args,
        **kwargs,
    ):
        # flows validation
        flows = flows if isinstance(flows, Flows) else Flows(flows=flows)

        # node lables validation
        start_node_label = normalize_node_label(start_node_label, flow_label="", default_priority=default_priority)
        if flows.get_node(start_node_label) is None:
            raise ValueError(f"Unkown {start_node_label=}")
        if fallback_node_label is None:
            fallback_node_label = start_node_label
        else:
            fallback_node_label = normalize_node_label(
                fallback_node_label,
                flow_label="",
                default_priority=default_priority,
            )
            if flows.get_node(fallback_node_label) is None:
                raise ValueError(f"Unkown {fallback_node_label}")

        # etc.
        default_priority = default_priority

        super(Actor, self).__init__(
            flows=flows,
            start_node_label=start_node_label,
            fallback_node_label=fallback_node_label,
            default_priority=default_priority,
            response_validation_flag=response_validation_flag,
            validation_logging_flag=validation_logging_flag,
            pre_handlers=pre_handlers,
            post_handlers=post_handlers,
        )
        errors = self.validate_flows(response_validation_flag, validation_logging_flag)
        if errors:
            raise ValueError(
                f"Found {len(errors)} errors: " + " ".join([f"{i}) {er}" for i, er in enumerate(errors, 1)])
            )

    @validate_arguments
    def __call__(
        self,
        ctx: Union[Context, dict, str] = {},
        return_dict=False,
        return_json=False,
        condition_handler: Callable = deep_copy_condition_handler,
        *args,
        **kwargs,
    ) -> Union[Context, dict, str]:
        if not ctx:
            ctx = Context()
            ctx.add_node_label(self.start_node_label[:2])
            ctx.add_human_utterance("")
        elif isinstance(ctx, dict):
            ctx = Context.parse_raw(ctx)
        elif isinstance(ctx, str):
            ctx = Context.parse_raw(ctx)
        elif not issubclass(type(ctx), Context):
            raise ValueError(
                f"context expexted as sub class of Context class or object of dict/str(json) type, but got {ctx}"
            )

        [handler(ctx, self, *args, **kwargs) for handler in self.pre_handlers]
        previous_node_label = (
            normalize_node_label(ctx.previous_node_label, "", self.default_priority)
            if ctx.previous_node_label
            else self.start_node_label
        )
        flow_label, node = self._get_node(previous_node_label)

        # TODO: deepcopy for node_label
        global_transitions = self.flows.get_transitions(self.default_priority, True)
        global_true_node_label = self._get_true_node_label(
            global_transitions,
            ctx,
            condition_handler,
            flow_label,
            "global",
        )

        local_transitions = node.get_transitions(flow_label, self.default_priority, False)
        local_true_node_label = self._get_true_node_label(
            local_transitions,
            ctx,
            condition_handler,
            flow_label,
            "local",
        )

        true_node_label = self._choose_true_node_label(local_true_node_label, global_true_node_label)

        ctx.add_node_label(true_node_label[:2])
        flow_label, next_node = self._get_node(true_node_label)
        processing = next_node.get_processing()
        _, tmp_node = processing(true_node_label, next_node, ctx, self, *args, **kwargs)

        response = tmp_node.get_response()
        text = response(ctx, self, *args, **kwargs)
        ctx.add_actor_utterance(text)

        [handler(ctx, self, *args, **kwargs) for handler in self.post_handlers]
        return ctx

    @validate_arguments
    def _get_true_node_label(
        self,
        transitions: dict,
        ctx: Context,
        condition_handler: Callable,
        flow_label: str,
        transition_info: str = "",
        *args,
        **kwargs,
    ) -> Optional[tuple[str, str, float]]:
        true_node_labels = []
        for node_label, condition in transitions.items():
            if condition_handler(condition, ctx, self, *args, **kwargs):
                if isinstance(node_label, Callable):
                    node_label = node_label(ctx, self, *args, **kwargs)
                    # TODO: explisit handling of errors
                    if node_label is None:
                        continue
                node_label = normalize_node_label(node_label, flow_label, self.default_priority)
                true_node_labels += [node_label]
        true_node_labels.sort(key=lambda label: -label[2])
        true_node_label = true_node_labels[0] if true_node_labels else None
        logger.debug(f"{transition_info} transitions sorted by priority = {true_node_labels}")
        return true_node_label

    @validate_arguments
    def _get_node(
        self,
        node_label: tuple[str, str, float],
    ) -> tuple[str, Node]:
        node = self.flows.get_node(node_label)
        if node is None:
            node, node_label = self.flows.get_node(self.start_node_label), self.start_node_label
        flow_label = node_label[0]
        return flow_label, node

    @validate_arguments
    def _choose_true_node_label(
        self,
        local_true_node_label: Optional[tuple[str, str, float]],
        global_true_node_label: Optional[tuple[str, str, float]],
    ) -> tuple[str, str, float]:
        if all([local_true_node_label, global_true_node_label]):
            true_node_label = (
                local_true_node_label
                if local_true_node_label[2] >= global_true_node_label[2]
                else global_true_node_label
            )
        elif any([local_true_node_label, global_true_node_label]):
            true_node_label = local_true_node_label if local_true_node_label else global_true_node_label
        else:
            true_node_label = self.fallback_node_label
        return true_node_label

    @validate_arguments
    def validate_flows(
        self,
        response_validation_flag: Optional[bool] = None,
        logging_flag: bool = True,
    ):
        transitions = self.flows.get_transitions(-1, False) | self.flows.get_transitions(-1, True)
        error_msgs = []
        for callable_node_label, condition in transitions.items():
            ctx = Context()
            ctx.add_human_utterance("text")
            actor = self.copy(deep=True)

            node_label = (
                callable_node_label(ctx, actor) if isinstance(callable_node_label, Callable) else callable_node_label
            )

            # validate node_label
            try:
                node = self.flows.get_node(node_label)
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
                    response_result = response_func(ctx, actor)
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
                bool(condition(ctx, actor))
            except Exception as exc:
                msg = f"Got exception '''{exc}''' during condition execution for {node_label=}"
                error_handler(error_msgs, msg, exc, logging_flag)
        return error_msgs
