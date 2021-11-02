import logging
from typing import Union, Callable, Optional


from pydantic import BaseModel, validate_arguments

from .types import ActorStage, NodeLabel2Type, NodeLabel3Type, LabelType

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
    handlers: dict[ActorStage, list[Callable]] = {}

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
        handlers: dict[ActorStage, list[Callable]] = {},
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
            if plot.get(fallback_label[0], {}).get(fallback_label[1]) is None:
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
            handlers=handlers,
        )
        errors = self.validate_plot(response_validation_flag, validation_logging_flag)
        if errors:
            raise ValueError(
                f"Found {len(errors)} errors: " + " ".join([f"{i}) {er}" for i, er in enumerate(errors, 1)])
            )

    @validate_arguments
    def __call__(self, ctx: Union[Context, dict, str] = {}, *args, **kwargs) -> Union[Context, dict, str]:

        # context init
        ctx = self._context_init(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.CONTEXT_INIT, *args, **kwargs)

        # get previous node
        ctx = self._get_previous_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.GET_PREVIOUS_NODE, *args, **kwargs)

        # get true labels for scopes (GLOBAL, LOCAL, NODE)
        ctx = self._get_true_labels(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.GET_TRUE_LABELS, *args, **kwargs)

        # get next node
        ctx = self._get_next_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.GET_NEXT_NODE, *args, **kwargs)

        ctx.add_label(ctx.a_s["next_label"][:2])

        # rewrite next node
        ctx = self._rewrite_next_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.REWRITE_NEXT_NODE, *args, **kwargs)

        # run processing
        ctx = self._run_processing(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.RUN_PROCESSING, *args, **kwargs)

        # create response
        ctx.a_s["response"] = ctx.a_s["processed_node"].response(ctx, self, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.CREATE_RESPONSE, *args, **kwargs)
        ctx.add_response(ctx.a_s["response"])

        self._run_handlers(ctx, ActorStage.FINISH_TURN, *args, **kwargs)
        ctx.a_s.clear()
        return ctx

    @validate_arguments
    def _context_init(self, ctx: Context, *args, **kwargs) -> Context:
        ctx = Context.cast(ctx)
        if not ctx.requests:
            ctx.add_label(self.start_label[:2])
            ctx.add_request("")
        return ctx

    @validate_arguments
    def _get_previous_node(self, ctx: Context, *args, **kwargs) -> Context:
        ctx.a_s["previous_label"] = normalize_label(ctx.last_label) if ctx.last_label else self.start_label
        ctx.a_s["previous_node"] = self.plot.get(ctx.a_s["previous_label"][0], {}).get(ctx.a_s["previous_label"][1])
        return ctx

    @validate_arguments
    def _get_true_labels(self, ctx: Context, *args, **kwargs) -> Context:
        # GLOBAL
        ctx.a_s["global_transitions"] = self.plot.get(GLOBAL, {}).get(GLOBAL, Node()).transitions
        ctx.a_s["global_true_label"] = self._get_true_label(ctx.a_s["global_transitions"], ctx, GLOBAL, "global")

        # LOCAL
        ctx.a_s["local_transitions"] = self.plot.get(ctx.a_s["previous_label"][0], {}).get(LOCAL, Node()).transitions
        ctx.a_s["local_true_label"] = self._get_true_label(
            ctx.a_s["local_transitions"],
            ctx,
            ctx.a_s["previous_label"][0],
            "local",
        )

        # NODE
        ctx.a_s["node_transitions"] = (
            self.plot.get(ctx.a_s["previous_label"][0], {}).get(ctx.a_s["previous_label"][1], Node()).transitions
        )
        ctx.a_s["node_true_label"] = self._get_true_label(
            ctx.a_s["node_transitions"],
            ctx,
            ctx.a_s["previous_label"][0],
            "node",
        )
        return ctx

    @validate_arguments
    def _get_next_node(self, ctx: Context, *args, **kwargs) -> Context:
        # choose next label
        ctx.a_s["next_label"] = self._choose_label(ctx.a_s["node_true_label"], ctx.a_s["local_true_label"])
        ctx.a_s["next_label"] = self._choose_label(ctx.a_s["next_label"], ctx.a_s["global_true_label"])
        # get next node
        ctx.a_s["next_node"] = self.plot.get(ctx.a_s["next_label"][0], {}).get(ctx.a_s["next_label"][1])
        if ctx.a_s["next_node"] is None:
            ctx.a_s["next_label"] = self.start_label
            ctx.a_s["next_node"] = self.plot.get(ctx.a_s["next_label"][0], {}).get(ctx.a_s["next_label"][1])
        return ctx

    @validate_arguments
    def _rewrite_next_node(self, ctx: Context, *args, **kwargs) -> Context:
        updated_next = self.plot.get(GLOBAL, {}).get(GLOBAL, Node()).copy()
        local_node = self.plot.get(ctx.a_s["next_label"][0], {}).get(LOCAL, Node())
        for node in [local_node, ctx.a_s["next_node"]]:
            updated_next.response = node.response if node.response else updated_next.response
            updated_next.processing.update(node.processing)
            updated_next.misc.update(node.misc)
        ctx.a_s["next_node"] = updated_next
        return ctx

    @validate_arguments
    def _run_processing(self, ctx: Context, *args, **kwargs) -> Context:
        ctx.a_s["processed_node"] = ctx.a_s["next_node"].copy()
        ctx = ctx.a_s["next_node"].processing(ctx, self, *args, **kwargs) if ctx.a_s["next_node"].processing else ctx
        return ctx

    @validate_arguments
    def _get_true_label(
        self,
        transitions: dict,
        ctx: Context,
        flow_label: LabelType,
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
        true_labels = [
            ((label[0] if label[0] else flow_label),)
            + label[1:2]
            + ((self.transition_priority if label[2] == float("-inf") else label[2]),)
            for label in true_labels
        ]
        true_labels.sort(key=lambda label: -label[2])
        true_label = true_labels[0] if true_labels else None
        logger.debug(f"{transition_info} transitions sorted by priority = {true_labels}")
        return true_label

    @validate_arguments
    def _run_handlers(self, ctx, actor_stade: ActorStage, *args, **kwargs):
        [handler(ctx, self, *args, **kwargs) for handler in self.handlers.get(actor_stade, [])]

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
