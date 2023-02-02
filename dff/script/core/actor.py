"""
Actor
---------------------------
Actor is one of the main abstractions that processes incoming requests
(:py:class:`~dff.script.Context`)
from the user in accordance with the dialog graph (:py:class:`~dff.script.Script`).
"""
import logging
from typing import Union, Callable, Optional, Dict, List, Any
import copy

from pydantic import BaseModel, validate_arguments, Extra

from dff.utils.turn_caching import cache_clear
from .types import ActorStage, NodeLabel2Type, NodeLabel3Type, LabelType
from .message import Message

from .context import Context
from .script import Script, Node
from .normalization import normalize_label, normalize_response
from .keywords import GLOBAL, LOCAL

logger = logging.getLogger(__name__)


def error_handler(error_msgs: list, msg: str, exception: Optional[Exception] = None, logging_flag: bool = True):
    """
    This function handles errors during :py:class:`~dff.script.Script` validation.

    :param error_msgs: List that contains error messages. :py:func:`~dff.script.error_handler`
        adds every next error message to that list.
    :param msg: Error message which is to be added into `error_msgs`.
    :param exception: Invoked exception. If it has been set, it is used to obtain logging traceback.
        Defaults to `None`.
    :param logging_flag: The flag which defines whether logging is necessary. Defaults to `True`.
    """
    error_msgs.append(msg)
    if logging_flag:
        logger.error(msg, exc_info=exception)


class Actor(BaseModel):
    """
    The class which is used to process :py:class:`~dff.script.Context`
    according to the :py:class:`~dff.script.Script`.
    """

    class Config:
        extra = Extra.allow

    script: Union[Script, dict]
    """
    The dialog scenario: a graph described by the :py:class:~dff.script.Keywords.
    While the graph is being initialized, it is validated and then used for the dialog.
    """
    start_label: NodeLabel3Type
    """
    The start node of :py:class:`~dff.script.Script`. The execution begins with it.
    """
    fallback_label: Optional[NodeLabel3Type] = None
    """
    The label of :py:class:`~dff.script.Script`.
    Dialog comes into that label if all other transitions failed, or there was an error while executing the scenario.
    Defaults to `None`.
    """
    label_priority: float = 1.0
    """
    Default priority value for all :py:const:`labels <dff.script.NodeLabel3Type>`
    where there is no priority. Defaults to `1.0`.
    """
    validation_stage: Optional[bool] = None
    """
    This flag sets whether the validation stage is executed. It is executed by default. Defaults to `None`.
    """
    condition_handler: Optional[Callable] = None
    """
    Handler that processes a call of condition functions. Defaults to `None`.
    """
    verbose: bool = True
    """
    If it is `True`, logging is used. Defaults to `True`.
    """
    handlers: Dict[ActorStage, List[Callable]] = {}
    """
    This variable is responsible for the usage of external handlers on
    the certain stages of work of :py:class:`~dff.script.Actor`.

        - key: :py:class:`~dff.script.ActorStage` - Stage in which the handler is called.
        - value: List[Callable] - The list of called handlers for each stage.

    Defaults to an empty `dict`.
    """

    @validate_arguments
    def __init__(
        self,
        script: Union[Script, dict],
        start_label: NodeLabel2Type,
        fallback_label: Optional[NodeLabel2Type] = None,
        label_priority: float = 1.0,
        validation_stage: Optional[bool] = None,
        condition_handler: Optional[Callable] = None,
        verbose: bool = True,
        handlers: Optional[Dict[ActorStage, List[Callable]]] = None,
        *args,
        **kwargs,
    ):
        # script validation
        script = script if isinstance(script, Script) else Script(script=script)

        # node labels validation
        start_label = normalize_label(start_label)
        if script.get(start_label[0], {}).get(start_label[1]) is None:
            raise ValueError(f"Unkown start_label={start_label}")
        if fallback_label is None:
            fallback_label = start_label
        else:
            fallback_label = normalize_label(fallback_label)
            if script.get(fallback_label[0], {}).get(fallback_label[1]) is None:
                raise ValueError(f"Unkown fallback_label={fallback_label}")
        if condition_handler is None:
            condition_handler = deep_copy_condition_handler

        super(Actor, self).__init__(
            script=script,
            start_label=start_label,
            fallback_label=fallback_label,
            label_priority=label_priority,
            validation_stage=validation_stage,
            condition_handler=condition_handler,
            verbose=verbose,
            handlers={} if handlers is None else handlers,
        )

        # NB! The following API is highly experimental and may be removed at ANY time WITHOUT FURTHER NOTICE!!
        self._clean_turn_cache = True

        errors = self.validate_script(verbose) if validation_stage or validation_stage is None else []
        if errors:
            raise ValueError(
                f"Found len(errors)={len(errors)} errors: " + " ".join([f"{i}) {er}" for i, er in enumerate(errors, 1)])
            )

    @validate_arguments
    def __call__(self, ctx: Optional[Union[Context, dict, str]] = None, *args, **kwargs) -> Union[Context, dict, str]:

        # context init
        ctx = self._context_init(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.CONTEXT_INIT, *args, **kwargs)

        # get previous node
        ctx = self._get_previous_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.GET_PREVIOUS_NODE, *args, **kwargs)

        # rewrite previous node
        ctx = self._rewrite_previous_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.REWRITE_PREVIOUS_NODE, *args, **kwargs)

        # run pre transitions processing
        ctx = self._run_pre_transitions_processing(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.RUN_PRE_TRANSITIONS_PROCESSING, *args, **kwargs)

        # get true labels for scopes (GLOBAL, LOCAL, NODE)
        ctx = self._get_true_labels(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.GET_TRUE_LABELS, *args, **kwargs)

        # get next node
        ctx = self._get_next_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.GET_NEXT_NODE, *args, **kwargs)

        ctx.add_label(ctx.framework_states["actor"]["next_label"][:2])

        # rewrite next node
        ctx = self._rewrite_next_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.REWRITE_NEXT_NODE, *args, **kwargs)

        # run pre response processing
        ctx = self._run_pre_response_processing(ctx, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.RUN_PRE_RESPONSE_PROCESSING, *args, **kwargs)

        # create response
        ctx.framework_states["actor"]["response"] = ctx.framework_states["actor"][
            "pre_response_processed_node"
        ].run_response(ctx, self, *args, **kwargs)
        self._run_handlers(ctx, ActorStage.CREATE_RESPONSE, *args, **kwargs)
        ctx.add_response(ctx.framework_states["actor"]["response"])

        self._run_handlers(ctx, ActorStage.FINISH_TURN, *args, **kwargs)
        if self._clean_turn_cache:
            cache_clear()

        del ctx.framework_states["actor"]
        return ctx

    @validate_arguments
    def _context_init(self, ctx: Optional[Union[Context, dict, str]] = None, *args, **kwargs) -> Context:
        ctx = Context.cast(ctx)
        if not ctx.requests:
            ctx.add_label(self.start_label[:2])
            ctx.add_request(Message())
        ctx.framework_states["actor"] = {}
        return ctx

    @validate_arguments
    def _get_previous_node(self, ctx: Context, *args, **kwargs) -> Context:
        ctx.framework_states["actor"]["previous_label"] = (
            normalize_label(ctx.last_label) if ctx.last_label else self.start_label
        )
        ctx.framework_states["actor"]["previous_node"] = self.script.get(
            ctx.framework_states["actor"]["previous_label"][0], {}
        ).get(ctx.framework_states["actor"]["previous_label"][1], Node())
        return ctx

    @validate_arguments
    def _get_true_labels(self, ctx: Context, *args, **kwargs) -> Context:
        # GLOBAL
        ctx.framework_states["actor"]["global_transitions"] = (
            self.script.get(GLOBAL, {}).get(GLOBAL, Node()).transitions
        )
        ctx.framework_states["actor"]["global_true_label"] = self._get_true_label(
            ctx.framework_states["actor"]["global_transitions"], ctx, GLOBAL, "global"
        )

        # LOCAL
        ctx.framework_states["actor"]["local_transitions"] = (
            self.script.get(ctx.framework_states["actor"]["previous_label"][0], {}).get(LOCAL, Node()).transitions
        )
        ctx.framework_states["actor"]["local_true_label"] = self._get_true_label(
            ctx.framework_states["actor"]["local_transitions"],
            ctx,
            ctx.framework_states["actor"]["previous_label"][0],
            "local",
        )

        # NODE
        ctx.framework_states["actor"]["node_transitions"] = ctx.framework_states["actor"][
            "pre_transitions_processed_node"
        ].transitions
        ctx.framework_states["actor"]["node_true_label"] = self._get_true_label(
            ctx.framework_states["actor"]["node_transitions"],
            ctx,
            ctx.framework_states["actor"]["previous_label"][0],
            "node",
        )
        return ctx

    @validate_arguments
    def _get_next_node(self, ctx: Context, *args, **kwargs) -> Context:
        # choose next label
        ctx.framework_states["actor"]["next_label"] = self._choose_label(
            ctx.framework_states["actor"]["node_true_label"], ctx.framework_states["actor"]["local_true_label"]
        )
        ctx.framework_states["actor"]["next_label"] = self._choose_label(
            ctx.framework_states["actor"]["next_label"], ctx.framework_states["actor"]["global_true_label"]
        )
        # get next node
        ctx.framework_states["actor"]["next_node"] = self.script.get(
            ctx.framework_states["actor"]["next_label"][0], {}
        ).get(ctx.framework_states["actor"]["next_label"][1])
        return ctx

    @validate_arguments
    def _rewrite_previous_node(self, ctx: Context, *args, **kwargs) -> Context:
        node = ctx.framework_states["actor"]["previous_node"]
        flow_label = ctx.framework_states["actor"]["previous_label"][0]
        ctx.framework_states["actor"]["previous_node"] = self._overwrite_node(
            node,
            flow_label,
            only_current_node_transitions=True,
        )
        return ctx

    @validate_arguments
    def _rewrite_next_node(self, ctx: Context, *args, **kwargs) -> Context:
        node = ctx.framework_states["actor"]["next_node"]
        flow_label = ctx.framework_states["actor"]["next_label"][0]
        ctx.framework_states["actor"]["next_node"] = self._overwrite_node(node, flow_label)
        return ctx

    @validate_arguments
    def _overwrite_node(
        self,
        current_node: Node,
        flow_label: LabelType,
        *args,
        only_current_node_transitions: bool = False,
        **kwargs,
    ) -> Node:
        overwritten_node = copy.deepcopy(self.script.get(GLOBAL, {}).get(GLOBAL, Node()))
        local_node = self.script.get(flow_label, {}).get(LOCAL, Node())
        for node in [local_node, current_node]:
            overwritten_node.pre_transitions_processing.update(node.pre_transitions_processing)
            overwritten_node.pre_response_processing.update(node.pre_response_processing)
            overwritten_node.response = overwritten_node.response if node.response is None else node.response
            overwritten_node.misc.update(node.misc)
            if not only_current_node_transitions:
                overwritten_node.transitions.update(node.transitions)
        if only_current_node_transitions:
            overwritten_node.transitions = current_node.transitions
        return overwritten_node

    @validate_arguments
    def _run_pre_transitions_processing(self, ctx: Context, *args, **kwargs) -> Context:
        ctx.framework_states["actor"]["processed_node"] = copy.deepcopy(ctx.framework_states["actor"]["previous_node"])
        ctx = ctx.framework_states["actor"]["previous_node"].run_pre_transitions_processing(ctx, self, *args, **kwargs)
        ctx.framework_states["actor"]["pre_transitions_processed_node"] = ctx.framework_states["actor"][
            "processed_node"
        ]
        del ctx.framework_states["actor"]["processed_node"]
        return ctx

    @validate_arguments
    def _run_pre_response_processing(self, ctx: Context, *args, **kwargs) -> Context:
        ctx.framework_states["actor"]["processed_node"] = copy.deepcopy(ctx.framework_states["actor"]["next_node"])
        ctx = ctx.framework_states["actor"]["next_node"].run_pre_response_processing(ctx, self, *args, **kwargs)
        ctx.framework_states["actor"]["pre_response_processed_node"] = ctx.framework_states["actor"]["processed_node"]
        del ctx.framework_states["actor"]["processed_node"]
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
                    # TODO: explicit handling of errors
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
    def validate_script(self, verbose: bool = True):
        # TODO: script has to not contain priority == -inf, because it uses for miss values
        flow_labels = []
        node_labels = []
        labels = []
        conditions = []
        for flow_name, flow in self.script.items():
            for node_name, node in flow.items():
                flow_labels += [flow_name] * len(node.transitions)
                node_labels += [node_name] * len(node.transitions)
                labels += list(node.transitions.keys())
                conditions += list(node.transitions.values())

        error_msgs = []
        for flow_label, node_label, label, condition in zip(flow_labels, node_labels, labels, conditions):
            ctx = Context()
            ctx.validation = True
            ctx.add_request(Message(text="text"))
            actor = self.copy(deep=True)

            label = label(ctx, actor) if isinstance(label, Callable) else normalize_label(label, flow_label)

            # validate labeling
            try:
                node = self.script[label[0]][label[1]]
            except Exception as exc:
                msg = (
                    f"Could not find node with label={label}, "
                    f"error was found in (flow_label, node_label)={(flow_label, node_label)}"
                )
                error_handler(error_msgs, msg, exc, verbose)
                break

            # validate responsing
            response_func = normalize_response(node.response)
            try:
                response_result = response_func(ctx, actor)
                if not isinstance(response_result, Message):
                    msg = (
                        "Expected type of response_result is `Message`.\n"
                        + f"Got type(response_result)={type(response_result)}"
                        f" for label={label} , error was found in (flow_label, node_label)={(flow_label, node_label)}"
                    )
                    error_handler(error_msgs, msg, None, verbose)
                    continue
            except Exception as exc:
                msg = (
                    f"Got exception '''{exc}''' during response execution "
                    f"for label={label} and node.response={node.response}"
                    f", error was found in (flow_label, node_label)={(flow_label, node_label)}"
                )
                error_handler(error_msgs, msg, exc, verbose)
                continue

            # validate conditioning
            try:
                condition_result = condition(ctx, actor)
                if not isinstance(condition(ctx, actor), bool):
                    raise Exception(f"Returned condition_result={condition_result}, but expected bool type")
            except Exception as exc:
                msg = f"Got exception '''{exc}''' during condition execution for label={label}"
                error_handler(error_msgs, msg, exc, verbose)
                continue
        return error_msgs


@validate_arguments()
def deep_copy_condition_handler(
    condition: Callable, ctx: Context, actor: Actor, *args, **kwargs
) -> Callable[[Context, Actor, Any, Any], bool]:
    """
    This function returns a deep copy of the callable conditions:

    :param condition: Condition to copy.
    :param ctx: Context of current condition.
    :param actor: Actor we use in this condition.
    """
    return condition(ctx.copy(deep=True), actor.copy(deep=True), *args, **kwargs)
