import logging
from typing import Union, Callable, Optional


from pydantic import BaseModel, validate_arguments

from .types import NodeLabel2Type, NodeLabel3Type

from .context import Context
from .plot import Plot, Node
from .normalization import normalize_label, normalize_response
from .keywords import GLOBAL, LOCAL


logger = logging.getLogger(__name__)
# TODO: add texts


def error_handler(error_msgs: list, msg: str, exception: Optional[Exception] = None, logging_flag: bool = True):
    error_msgs.append(msg)
    logging_flag and logger.error(msg, exc_info=exception)


class Actor(BaseModel):
    plot: Union[Plot, dict]
    start_label: NodeLabel3Type
    fallback_label: Optional[NodeLabel3Type] = None
    transition_priority: float = 1.0
    response_validation_flag: Optional[bool] = None
    condition_handler: Optional[Callable] = None
    validation_logging_flag: bool = True
    pre_handlers: list[Callable] = []
    post_handlers: list[Callable] = []

    @validate_arguments
    def __init__(
        self,
        plot: Union[Plot, dict],
        start_label: NodeLabel2Type,
        fallback_label: Optional[NodeLabel2Type] = None,
        transition_priority: float = 1.0,
        response_validation_flag: Optional[bool] = None,
        condition_handler: Optional[Callable] = None,
        validation_logging_flag: bool = True,
        pre_handlers: list[Callable] = [],
        post_handlers: list[Callable] = [],
        *args,
        **kwargs,
    ):
        # plot validation
        plot = plot if isinstance(plot, Plot) else Plot(plot=plot)

        # node lables validation
        start_label = normalize_label(start_label)
        if plot.get(start_label[0], {}).get(start_label[1]) is None:
            raise ValueError(f"Unkown {start_label=}")
        if fallback_label is None:
            fallback_label = start_label
        else:
            fallback_label = normalize_label(fallback_label)
            if plot.get(fallback_label[0]).get(fallback_label[1]) is None:
                raise ValueError(f"Unkown {fallback_label=}")
        if condition_handler is None:
            condition_handler = deep_copy_condition_handler

        super(Actor, self).__init__(
            plot=plot,
            start_label=start_label,
            fallback_label=fallback_label,
            transition_priority=transition_priority,
            response_validation_flag=response_validation_flag,
            condition_handler=condition_handler,
            validation_logging_flag=validation_logging_flag,
            pre_handlers=pre_handlers,
            post_handlers=post_handlers,
        )
        errors = self.validate_plot(response_validation_flag, validation_logging_flag)
        if errors:
            raise ValueError(
                f"Found {len(errors)} errors: " + " ".join([f"{i}) {er}" for i, er in enumerate(errors, 1)])
            )

    @validate_arguments
    def __call__(
        self,
        ctx: Union[Context, dict, str] = {},
        *args,
        **kwargs,
    ) -> Union[Context, dict, str]:
        ctx = Context.cast(ctx)
        if not ctx.requests:
            ctx.add_label(self.start_label[:2])
            ctx.add_request("")

        [handler(ctx, self, *args, **kwargs) for handler in self.pre_handlers]
        previous_label = normalize_label(ctx.last_label) if ctx.last_label else self.start_label
        previous_node = self.plot.get(previous_label[0], {}).get(previous_label[1])
        ctx.actor_state["previous_label"] = previous_label
        ctx.actor_state["previous_node"] = previous_node

        global_transitions = self.plot.get(GLOBAL, {}).get(GLOBAL, Node()).transitions
        global_true_label = self._get_true_label(global_transitions, ctx, GLOBAL, "global")

        local_transitions = self.plot.get(previous_label[0], {}).get(LOCAL, Node()).transitions
        local_true_label = self._get_true_label(local_transitions, ctx, previous_label[0], "local")

        node_transitions = self.plot.get(previous_label[0], {}).get(previous_label[1], Node()).transitions
        node_true_label = self._get_true_label(node_transitions, ctx, previous_label[0], "node")

        next_label = self._choose_label(node_true_label, local_true_label)
        next_label = self._choose_label(next_label, global_true_label)

        next_node = self.plot.get(next_label[0], {}).get(next_label[1])
        if next_node is None:
            next_label = self.start_label
            next_node = self.plot.get(next_label[0], {}).get(next_label[1])
        ctx.actor_state["next_label"] = next_label
        ctx.actor_state["next_node"] = next_node
        ctx.add_label(next_label[:2])

        ctx = next_node.processing(ctx, self, *args, **kwargs) if next_node.processing else ctx

        response = ctx.actor_state["next_node"].response(ctx, self, *args, **kwargs)
        ctx.add_response(response)

        [handler(ctx, self, *args, **kwargs) for handler in self.post_handlers]
        return ctx

    @validate_arguments
    def _get_true_label(
        self,
        transitions: dict,
        ctx: Context,
        flow_label: str,
        transition_info: str = "",
        *args,
        **kwargs,
    ) -> Optional[NodeLabel3Type]:
        true_labels = []
        for label, condition in transitions.items():
            if self.condition_handler(condition, ctx, self, *args, **kwargs):
                if isinstance(label, Callable):
                    label = label(ctx, self, *args, **kwargs)
                    # TODO: explisit handling of errors
                    if label is None:
                        continue
                label = normalize_label(label, flow_label)
                true_labels += [label]
        true_labels.sort(key=lambda label: -(self.transition_priority if label[2] == float("-inf") else label[2]))
        true_label = (flow_label,) + true_labels[0][1:] if true_labels else None
        logger.debug(f"{transition_info} transitions sorted by priority = {true_labels}")
        return true_label

    @validate_arguments
    def _choose_label(
        self,
        specific_label: Optional[NodeLabel3Type],
        general_label: Optional[NodeLabel3Type],
    ) -> NodeLabel3Type:
        if all([specific_label, general_label]):
            chosen_label = specific_label if specific_label[2] >= general_label[2] else general_label
        elif any([specific_label, general_label]):
            chosen_label = specific_label if specific_label else general_label
        else:
            chosen_label = self.fallback_label
        return chosen_label

    @validate_arguments
    def validate_plot(
        self,
        response_validation_flag: Optional[bool] = None,
        logging_flag: bool = True,
    ):
        # TODO: plot has to not contain priority == -inf, because it uses for miss values
        labels = []
        conditions = []
        for flow in self.plot.values():
            for node in flow.values():
                labels += list(node.transitions.keys())
                conditions += list(node.transitions.values())

        error_msgs = []
        for label, condition in zip(labels, conditions):
            ctx = Context()
            ctx.validation = True
            ctx.add_request("text")
            actor = self.copy(deep=True)

            label = label(ctx, actor) if isinstance(label, Callable) else label

            try:
                node = self.plot.get(label[0], {}).get(label[1], Node())
            except Exception as exc:
                node = None
                msg = f"Got exception '''{exc}''' for {label=}"
                error_handler(error_msgs, msg, exc, logging_flag)

            if not isinstance(node, Node):
                msg = f"Could not find node with {label=}"
                error_handler(error_msgs, msg, None, logging_flag)
                continue

            # validate response
            if response_validation_flag or response_validation_flag is None:
                response_func = normalize_response(node.response)
                n_errors = len(error_msgs)
                try:
                    response_result = response_func(ctx, actor)
                    if isinstance(response_result, Callable):
                        msg = (
                            f"Expected type of response_result needed not Callable but got {type(response_result)=}"
                            f" for {label=}"
                        )
                        error_handler(error_msgs, msg, None, logging_flag)
                except Exception as exc:
                    msg = f"Got exception '''{exc}''' during response execution " f"for {label=} and {node.response=}"
                    error_handler(error_msgs, msg, exc, logging_flag)
                if n_errors != len(error_msgs) and response_validation_flag is None:
                    logger.info(
                        "response_validation_flag was not setuped, by default responses validation is enabled. "
                        "It's service message can be switched off by manually setting response_validation_flag"
                    )

            # validate conditions
            try:
                bool(condition(ctx, actor))
            except Exception as exc:
                msg = f"Got exception '''{exc}''' during condition execution for {label=}"
                error_handler(error_msgs, msg, exc, logging_flag)
        return error_msgs


@validate_arguments()
def deep_copy_condition_handler(condition: Callable, ctx: Context, actor: Actor, *args, **kwargs):
    return condition(ctx.copy(deep=True), actor.copy(deep=True), *args, **kwargs)
