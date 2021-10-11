import logging
from typing import Union, Callable, Optional
import copy


from pydantic import BaseModel, validate_arguments

from .keywords import GLOBAL, GRAPH, LOCAL, GLOBAL_TRANSITIONS, MISC, PROCESSING, RESPONSE, TRANSITIONS
from .context import Context
from .plot import Plot, Node
from .normalization import normalize_node_label, normalize_response


logger = logging.getLogger(__name__)
# TODO: add texts


def error_handler(error_msgs: list, msg: str, exception: Optional[Exception] = None, logging_flag: bool = True):
    error_msgs.append(msg)
    logging_flag and logger.error(msg, exc_info=exception)


@validate_arguments
def check_cond_seq(cond_seq):
    for cond in cond_seq:
        if not isinstance(cond, Callable):
            raise Exception(f"{cond_seq=} has to consist of callable objects")


def aggregate(cond_seq: list, *args, **kwargs):
    check_cond_seq(cond_seq)

    def aggregate_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        try:
            return bool(all([cond(ctx, actor, *args, **kwargs) for cond in cond_seq]))
        except Exception as exc:
            logger.error(f"Exception {exc} for {cond_seq=}, {all=} and {ctx.last_request=}", exc_info=exc)

    return aggregate_condition_handler


@validate_arguments
def isin_flow(flows: list[str] = [], nodes: list[tuple[str, str]] = [], *args, **kwargs):
    def isin_flow_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        node_label = list(ctx.node_labels.values())
        node_label = node_label[-1][:2] if node_label else (None, None)
        return node_label[0] in flows or node_label in nodes

    return isin_flow_condition_handler


@validate_arguments
def downgrade_plot_version(plot: dict):
    plot = copy.deepcopy(plot)
    global_flow = {}
    for plot_key in list(plot.keys()):
        if GLOBAL == plot_key:
            node = plot[plot_key]
            del plot[plot_key]
            node[GLOBAL_TRANSITIONS] = node[TRANSITIONS]
            del node[TRANSITIONS]
            global_flow[plot_key] = node
        else:
            for flow_key in plot[plot_key].keys():
                if flow_key == LOCAL:
                    node = plot[plot_key][flow_key]
                    del plot[plot_key][flow_key]
                    node[GLOBAL_TRANSITIONS] = node[TRANSITIONS]
                    del node[TRANSITIONS]
                    node[GLOBAL_TRANSITIONS] = {
                        tr_key: aggregate([tr_val, isin_flow([flow_key])])
                        for tr_key, tr_val in node[GLOBAL_TRANSITIONS].items()
                    }
                    global_flow[plot_key] = node

    for plot_key in list(plot.keys()):
        for flow_key in plot[plot_key].keys():
            processing = global_flow.get(GLOBAL, {}).get(PROCESSING, {}).copy()
            upd_processing = global_flow.get(plot_key, {}).get(PROCESSING, {})
            if isinstance(processing, dict) and isinstance(upd_processing, dict):
                processing.update(upd_processing)
            else:
                processing = upd_processing

            upd_processing = plot[plot_key][flow_key].get(PROCESSING, {})
            if isinstance(processing, dict) and isinstance(upd_processing, dict):
                processing.update(upd_processing)
            else:
                processing = upd_processing
            plot[plot_key][flow_key][PROCESSING] = processing

    for plot_key in list(plot.keys()):
        for flow_key in plot[plot_key].keys():
            misc = global_flow.get(GLOBAL, {}).get(MISC, {}).copy()
            upd_misc = global_flow.get(plot_key, {}).get(MISC, {})
            if isinstance(misc, dict) and isinstance(upd_misc, dict):
                misc.update(upd_misc)
            else:
                misc = upd_misc

            upd_misc = plot[plot_key][flow_key].get(MISC, {})
            if isinstance(misc, dict) and isinstance(upd_misc, dict):
                misc.update(upd_misc)
            else:
                misc = upd_misc
            plot[plot_key][flow_key][MISC] = misc

    for plot_key in list(plot.keys()):
        for flow_key in plot[plot_key].keys():
            response = global_flow.get(GLOBAL, {}).get(RESPONSE, "")
            response = global_flow.get(plot_key, {}).get(RESPONSE, response)
            response = plot[plot_key][flow_key].get(RESPONSE, response)
            plot[plot_key][flow_key][RESPONSE] = response

    plot["global.flow"] = global_flow

    for plot_key in list(plot.keys()):
        for flow_key in plot[plot_key].keys():
            processing = plot[plot_key][flow_key].get(PROCESSING, {})
            if isinstance(processing, dict):
                plot[plot_key][flow_key][PROCESSING] = list(processing.values())
            if not plot[plot_key][flow_key][PROCESSING]:
                del plot[plot_key][flow_key][PROCESSING]
    global_flow = plot["global.flow"]
    del plot["global.flow"]

    for plot_key in list(plot.keys()):
        plot[plot_key] = {GRAPH: plot[plot_key]}
        plot[plot_key][GLOBAL_TRANSITIONS] = global_flow.get(flow_key, {}).get(GLOBAL_TRANSITIONS, {})
    plot["global.flow"] = {GLOBAL_TRANSITIONS: global_flow.get(GLOBAL, {}).get(GLOBAL_TRANSITIONS, {})}
    return plot


class Actor(BaseModel):
    plot: Union[Plot, dict]
    start_node_label: tuple[str, str, float]
    fallback_node_label: Optional[tuple[str, str, float]] = None
    default_transition_priority: float = 1.0
    response_validation_flag: Optional[bool] = None
    validation_logging_flag: bool = True
    pre_handlers: list[Callable] = []
    post_handlers: list[Callable] = []

    @validate_arguments
    def __init__(
        self,
        plot: Union[Plot, dict],
        start_node_label: tuple[str, str],
        fallback_node_label: Optional[tuple[str, str]] = None,
        default_transition_priority: float = 1.0,
        response_validation_flag: Optional[bool] = None,
        validation_logging_flag: bool = True,
        pre_handlers: list[Callable] = [],
        post_handlers: list[Callable] = [],
        *args,
        **kwargs,
    ):
        # plot validation
        plot = plot if isinstance(plot, Plot) else Plot(plot=downgrade_plot_version(plot))

        # node lables validation
        start_node_label = normalize_node_label(
            start_node_label, flow_label="", default_transition_priority=default_transition_priority
        )
        if plot.get_node(start_node_label) is None:
            raise ValueError(f"Unkown {start_node_label=}")
        if fallback_node_label is None:
            fallback_node_label = start_node_label
        else:
            fallback_node_label = normalize_node_label(
                fallback_node_label,
                flow_label="",
                default_transition_priority=default_transition_priority,
            )
            if plot.get_node(fallback_node_label) is None:
                raise ValueError(f"Unkown {fallback_node_label}")

        # etc.
        default_transition_priority = default_transition_priority

        super(Actor, self).__init__(
            plot=plot,
            start_node_label=start_node_label,
            fallback_node_label=fallback_node_label,
            default_transition_priority=default_transition_priority,
            response_validation_flag=response_validation_flag,
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
        return_dict=False,
        return_json=False,
        condition_handler: Optional[Callable] = None,
        *args,
        **kwargs,
    ) -> Union[Context, dict, str]:
        ctx = Context.cast(ctx)
        if not ctx.requests:
            ctx.add_node_label(self.start_node_label[:2])
            ctx.add_request("")
        if condition_handler is None:
            condition_handler = deep_copy_condition_handler

        [handler(ctx, self, *args, **kwargs) for handler in self.pre_handlers]
        previous_node_label = (
            normalize_node_label(ctx.previous_node_label, "", self.default_transition_priority)
            if ctx.previous_node_label
            else self.start_node_label
        )
        flow_label, node = self._get_node(previous_node_label)

        # TODO: deepcopy for node_label
        global_transitions = self.plot.get_transitions(self.default_transition_priority, True)
        global_true_node_label = self._get_true_node_label(
            global_transitions,
            ctx,
            condition_handler,
            flow_label,
            "global",
        )

        local_transitions = node.get_transitions(flow_label, self.default_transition_priority, False)
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
        ctx.add_response(text)

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
                node_label = normalize_node_label(node_label, flow_label, self.default_transition_priority)
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
        node = self.plot.get_node(node_label)
        if node is None:
            node, node_label = self.plot.get_node(self.start_node_label), self.start_node_label
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
    def validate_plot(
        self,
        response_validation_flag: Optional[bool] = None,
        logging_flag: bool = True,
    ):
        transitions = self.plot.get_transitions(-1, False) | self.plot.get_transitions(-1, True)
        error_msgs = []
        for callable_node_label, condition in transitions.items():
            ctx = Context()
            ctx.validation = True
            ctx.add_request("text")
            actor = self.copy(deep=True)

            if hasattr(callable_node_label, "update_forward_refs"):
                callable_node_label.update_forward_refs()
            node_label = (
                callable_node_label(ctx, actor) if isinstance(callable_node_label, Callable) else callable_node_label
            )

            # validate node_label
            try:
                node = self.plot.get_node(node_label)
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
                    if isinstance(response_result, Callable):
                        msg = (
                            f"Expected type of response_result needed not Callable but got {type(response_result)=}"
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


@validate_arguments()
def deep_copy_condition_handler(condition: Callable, ctx: Context, actor: Actor, *args, **kwargs):
    return condition(ctx.copy(deep=True), actor.copy(deep=True), *args, **kwargs)
