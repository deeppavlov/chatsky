"""
Actor
---------------------------
The Actor is described here.
Actor is one of the main abstractions that processes incoming requests (:py:class:`~df_engine.core.context.Context`)
from the user in accordance with the dialog graph (:py:class:`~df_engine.core.plot.Plot`).
"""
import logging
from typing import Union, Callable, Optional
import copy

from pydantic import BaseModel, validate_arguments

from .types import ActorStage, NodeLabel2Type, NodeLabel3Type, LabelType

from .context import Context
from .plot import Plot, Node
from .normalization import normalize_label, normalize_response
from .keywords import GLOBAL, LOCAL

logger = logging.getLogger(__name__)


def error_handler(error_msgs: list, msg: str, exception: Optional[Exception] = None, logging_flag: bool = True):
    """
    This function processes errors in the process of :py:class:`~df_engine.core.plot.Plot` validation.

    Parameters
    ----------
    error_msgs : list
       List that contains error messages. :py:func:`~df_engine.core.actor.error_handler`
       adds every next error message to that list.
    msg: str
        Error message which is to be added into `error_msgs`.
    exception : Optional[Exception]
        Invoked exception. If it was set, it is used to obtain logging traceback.
    logging_flag : bool
        The flag which defines whether logging is nesessary.
    """
    error_msgs.append(msg)
    logging_flag and logger.error(msg, exc_info=exception)


class Actor(BaseModel):
    """
    The class which is used to process :py:class:`~df_engine.core.context.Context`
    according to the :py:class:`~df_engine.core.plot.Plot`.

    Parameters
    ----------

    plot: Union[Plot, dict]
       The dialog scenario: a graph described by the :py:class:`~df_engine.core.keywords.Keywords`.
       While the graph is being initialized, it passes validation and after that it is used for the dialog.

    start_label: :py:const:`~df_engine.core.types.NodeLabel3Type`
       The start node of :py:class:`~df_engine.core.plot.Plot`. The execution starts from it.

    fallback_label: Optional[:py:const:`~df_engine.core.types.NodeLabel3Type`] = None
       The label of :py:class:`~df_engine.core.plot.Plot`.
       Dialog comes into that label if all other transitions failed, or there was an error while executing the scenario.

    label_priority: float = 1.0
       Default priority value for all :py:const:`labels <df_engine.core.types.NodeLabel3Type>`
       where there is no priority.

    validation_stage: Optional[bool] = None
       This flag sets whether the validation stage is executed. It is executed by default.

    condition_handler: Optional[Callable] = None
       Handler that processes a call of condition functions.

    verbose: bool = True
        If it is True, we use logging.

    handlers: dict[ActorStage, list[Callable]] = {}
        This variable is responsible for the usage of external handlers on
        the certain stages of work of :py:class:`~df_engine.core.actor.Actor`.

        * key: :py:class:`~df_engine.core.types.ActorStage` - stage when the handler is called
        * value: list[Callable] - the list of called handlers for each stage
    """

    plot: Union[Plot, dict]
    start_label: NodeLabel3Type
    fallback_label: Optional[NodeLabel3Type] = None
    label_priority: float = 1.0
    validation_stage: Optional[bool] = None
    condition_handler: Optional[Callable] = None
    verbose: bool = True
    handlers: dict[ActorStage, list[Callable]] = {}

    @validate_arguments
    def __init__(
        self,
        plot: Union[Plot, dict],
        start_label: NodeLabel2Type,
        fallback_label: Optional[NodeLabel2Type] = None,
        label_priority: float = 1.0,
        validation_stage: Optional[bool] = None,
        condition_handler: Optional[Callable] = None,
        verbose: bool = True,
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
            label_priority=label_priority,
            validation_stage=validation_stage,
            condition_handler=condition_handler,
            verbose=verbose,
            handlers=handlers,
        )
        errors = self.validate_plot(verbose) if validation_stage or validation_stage is None else []
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
        ctx.a_s["response"] = ctx.a_s["processed_node"].run_response(ctx, self, *args, **kwargs)
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
            ctx.a_s["local_transitions"], ctx, ctx.a_s["previous_label"][0], "local"
        )

        # NODE
        ctx.a_s["node_transitions"] = (
            self.plot.get(ctx.a_s["previous_label"][0], {}).get(ctx.a_s["previous_label"][1], Node()).transitions
        )
        ctx.a_s["node_true_label"] = self._get_true_label(
            ctx.a_s["node_transitions"], ctx, ctx.a_s["previous_label"][0], "node"
        )
        return ctx

    @validate_arguments
    def _get_next_node(self, ctx: Context, *args, **kwargs) -> Context:
        # choose next label
        ctx.a_s["next_label"] = self._choose_label(ctx.a_s["node_true_label"], ctx.a_s["local_true_label"])
        ctx.a_s["next_label"] = self._choose_label(ctx.a_s["next_label"], ctx.a_s["global_true_label"])
        # get next node
        ctx.a_s["next_node"] = self.plot.get(ctx.a_s["next_label"][0], {}).get(ctx.a_s["next_label"][1])
        # below is commented unreachable condition
        # if ctx.a_s["next_node"] is None:
        #     ctx.a_s["next_label"] = self.start_label
        #     ctx.a_s["next_node"] = self.plot.get(ctx.a_s["next_label"][0], {}).get(ctx.a_s["next_label"][1])
        return ctx

    @validate_arguments
    def _rewrite_next_node(self, ctx: Context, *args, **kwargs) -> Context:
        updated_next = copy.deepcopy(self.plot.get(GLOBAL, {}).get(GLOBAL, Node()))
        local_node = self.plot.get(ctx.a_s["next_label"][0], {}).get(LOCAL, Node())
        for node in [local_node, ctx.a_s["next_node"]]:
            updated_next.response = node.response if node.response else updated_next.response
            updated_next.processing.update(node.processing)
            updated_next.misc.update(node.misc)
        ctx.a_s["next_node"] = updated_next
        return ctx

    @validate_arguments
    def _run_processing(self, ctx: Context, *args, **kwargs) -> Context:
        ctx.a_s["processed_node"] = copy.deepcopy(ctx.a_s["next_node"])
        ctx = ctx.a_s["next_node"].run_processing(ctx, self, *args, **kwargs)
        return ctx

    @validate_arguments
    def _get_true_label(
        self, transitions: dict, ctx: Context, flow_label: LabelType, transition_info: str = "", *args, **kwargs
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
            + ((self.label_priority if label[2] == float("-inf") else label[2]),)
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
        self, specific_label: Optional[NodeLabel3Type], general_label: Optional[NodeLabel3Type]
    ) -> NodeLabel3Type:
        if all([specific_label, general_label]):
            chosen_label = specific_label if specific_label[2] >= general_label[2] else general_label
        elif any([specific_label, general_label]):
            chosen_label = specific_label if specific_label else general_label
        else:
            chosen_label = self.fallback_label
        return chosen_label

    @validate_arguments
    def validate_plot(self, verbose: bool = True):
        # TODO: plot has to not contain priority == -inf, because it uses for miss values
        flow_labels = []
        node_labels = []
        labels = []
        conditions = []
        for flow_name, flow in self.plot.items():
            for node_name, node in flow.items():
                flow_labels += [flow_name] * len(node.transitions)
                node_labels += [node_name] * len(node.transitions)
                labels += list(node.transitions.keys())
                conditions += list(node.transitions.values())

        error_msgs = []
        for flow_label, node_label, label, condition in zip(flow_labels, node_labels, labels, conditions):
            ctx = Context()
            ctx.validation = True
            ctx.add_request("text")
            actor = self.copy(deep=True)

            label = label(ctx, actor) if isinstance(label, Callable) else normalize_label(label, flow_label)

            # validate labeling
            try:
                node = self.plot[label[0]][label[1]]
            except Exception as exc:
                msg = f"Could not find node with {label=}, error was found in {(flow_label, node_label)}"
                error_handler(error_msgs, msg, exc, verbose)
                break

            # validate responsing
            response_func = normalize_response(node.response)
            try:
                response_result = response_func(ctx, actor)
                if isinstance(response_result, Callable):
                    msg = (
                        f"Expected type of response_result needed not Callable but got {type(response_result)=}"
                        f" for {label=} , error was found in {(flow_label, node_label)}"
                    )
                    error_handler(error_msgs, msg, None, verbose)
                    continue
            except Exception as exc:
                msg = (
                    f"Got exception '''{exc}''' during response execution "
                    f"for {label=} and {node.response=}"
                    f", error was found in {(flow_label, node_label)}"
                )
                error_handler(error_msgs, msg, exc, verbose)
                continue

            # validate conditioning
            try:
                condition_result = condition(ctx, actor)
                if not isinstance(condition(ctx, actor), bool):
                    raise Exception(f"Returned {condition_result=}, but expected bool type")
            except Exception as exc:
                msg = f"Got exception '''{exc}''' during condition execution for {label=}"
                error_handler(error_msgs, msg, exc, verbose)
                continue
        return error_msgs


@validate_arguments()
def deep_copy_condition_handler(condition: Callable, ctx: Context, actor: Actor, *args, **kwargs):
    """
    This function returns deep copy of callable conditions:

    Parameters
    ----------

    condition: Callable
        condition to copy
    ctx: Context
        context of current condition
    actor: Actor
        :py:class:`~df_engine.core.actor.Actor` we use in this condition
    """
    return condition(ctx.copy(deep=True), actor.copy(deep=True), *args, **kwargs)
