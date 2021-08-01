import heapq
from typing import Union, Optional, Callable

from pydantic import validate_arguments, BaseModel

from dff.core.flows import Flows, Node, normalize_node_label
from dff.core.context import Context
from dff.core.condition_handlers import deep_copy_condition_handler

# TODO: add texts


class Actor(BaseModel):
    flows: Union[Flows, dict]
    start_node_label: tuple[str, str, float]
    fallback_node_label: Optional[tuple[str, str, float]] = None
    default_priority: float = 1.0
    response_validation_flag: Optional[bool] = None
    validation_logging_flag: bool = True

    @validate_arguments
    def __init__(
        self,
        flows: Union[Flows, dict],
        start_node_label: tuple[str, str],
        fallback_node_label: Optional[tuple[str, str]] = None,
        default_priority: float = 1.0,
        response_validation_flag: Optional[bool] = None,
        validation_logging_flag: bool = True,
        *args,
        **kwargs,
    ):
        # flows validation
        flows = flows if isinstance(flows, Flows) else Flows(flows=flows)
        errors = flows.validate_flows(response_validation_flag, validation_logging_flag)
        if errors:
            raise ValueError(
                f"Found {len(errors)} errors: " + " ".join([f"{i}) {er}" for i, er in enumerate(errors, 1)])
            )

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

        return super(Actor, self).__init__(
            flows=flows,
            start_node_label=start_node_label,
            fallback_node_label=fallback_node_label,
            default_priority=default_priority,
            response_validation_flag=response_validation_flag,
            validation_logging_flag=validation_logging_flag,
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

        previous_node_label = (
            normalize_node_label(ctx.previous_node_label, "", self.default_priority)
            if ctx.previous_node_label
            else self.start_node_label
        )
        flow_label, node = self.get_node(previous_node_label)

        # TODO: deepcopy for node_label
        global_transitions = self.flows.get_transitions(self.default_priority, True)
        global_true_node_label = self.get_true_node_label(global_transitions, ctx, condition_handler, flow_label)

        local_transitions = node.get_transitions(flow_label, self.default_priority, False)
        local_true_node_label = self.get_true_node_label(local_transitions, ctx, condition_handler, flow_label)

        true_node_label = self.choose_true_node_label(local_true_node_label, global_true_node_label)

        ctx.add_node_label(true_node_label[:2])
        flow_label, next_node = self.get_node(true_node_label)
        processing = next_node.get_processing()
        _, tmp_node = processing(flow_label, next_node, ctx, self.flows, *args, **kwargs)

        response = tmp_node.get_response()
        text = response(ctx, self.flows, *args, **kwargs)
        ctx.add_actor_utterance(text)

        return ctx

    @validate_arguments
    def get_true_node_label(
        self,
        transitions: dict,
        ctx: Context,
        condition_handler: Callable,
        flow_label: str,
        *args,
        **kwargs,
    ) -> Optional[tuple[str, str, float]]:
        true_node_labels = []
        for node_label, condition in transitions.items():
            if condition_handler(condition, ctx, self.flows, *args, **kwargs):
                if isinstance(node_label, Callable):
                    node_label = node_label(ctx, self.flows, *args, **kwargs)
                    if node_label is None:
                        continue
                node_label = normalize_node_label(node_label, flow_label, self.default_priority)
                heapq.heappush(true_node_labels, (node_label[2], node_label))
        true_node_label = true_node_labels[0][1] if true_node_labels else None
        return true_node_label

    @validate_arguments
    def get_node(
        self,
        node_label: tuple[str, str, float],
    ) -> tuple[str, Node]:
        node = self.flows.get_node(node_label)
        if node is None:
            node, node_label = self.flows.get_node(self.start_node_label), self.start_node_label
        flow_label = node_label[0]
        return flow_label, node

    @validate_arguments
    def choose_true_node_label(
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
