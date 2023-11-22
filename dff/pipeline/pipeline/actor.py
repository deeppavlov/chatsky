"""
Actor
-----
Actor is a component of :py:class:`.Pipeline`, that contains the :py:class:`.Script` and handles it.
It is responsible for processing user input and determining the appropriate response based
on the current state of the conversation and the script.
The actor receives requests in the form of a :py:class:`.Context` class, which contains
information about the user's input, the current state of the conversation, and other relevant data.

The actor uses the dialog graph, represented by the :py:class:`.Script` class,
to determine the appropriate response. The script contains the structure of the conversation,
including the different `nodes` and `transitions`.
It defines the possible paths that the conversation can take, and the conditions that must be met
for a transition to occur. The actor uses this information to navigate the graph
and determine the next step in the conversation.

Overall, the actor acts as a bridge between the user's input and the dialog graph,
making sure that the conversation follows the expected flow and providing a personalized experience to the user.

Below you can see a diagram of user request processing with Actor.
Both `request` and `response` are saved to :py:class:`.Context`.

.. figure:: /_static/drawio/dfe/user_actor.png
"""
import inspect
import logging
from typing import Union, Callable, Optional, Dict, List, Any, ForwardRef
import copy

from dff.utils.turn_caching import cache_clear
from dff.script.core.types import ActorStage, NodeLabel2Type, NodeLabel3Type, LabelType
from dff.script.core.message import Message

from dff.script.core.context import Context
from dff.script.core.script import Script, Node
from dff.script.core.normalization import normalize_label, normalize_response
from dff.script.core.keywords import GLOBAL, LOCAL

logger = logging.getLogger(__name__)

Pipeline = ForwardRef("Pipeline")


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


def validate_callable(callable: Callable, name: str, flow_label: str, node_label: str, error_msgs: list, verbose: bool, expected: Optional[list] = None, rtrn = None):
    signature = inspect.signature(callable)
    if expected is not None:
        params = list(signature.parameters.values())
        if len(params) != len(expected):
            msg = (
                f"Incorrect parameter number of {name}={callable.__name__}: "
                f"should be {len(expected)}, found {len(params)}, "
                f"error was found in (flow_label, node_label)={(flow_label, node_label)}"
            )
            error_handler(error_msgs, msg, None, verbose)
        for idx, param in enumerate(params):
            if param.annotation != inspect.Parameter.empty and param.annotation != expected[idx]:
                msg = (
                    f"Incorrect {idx} parameter annotation of {name}={callable.__name__}: "
                    f"should be {expected[idx]}, found {param.annotation}, "
                    f"error was found in (flow_label, node_label)={(flow_label, node_label)}"
                )
                error_handler(error_msgs, msg, None, verbose)
    if rtrn is not None:
        rtrn_type = signature.return_annotation
        if rtrn_type != inspect.Parameter.empty and rtrn_type != rtrn:
            msg = (
                f"Incorrect return type annotation of {name}={callable.__name__}: "
                f"should be {len(rtrn)}, found {len(rtrn_type)}, "
                f"error was found in (flow_label, node_label)={(flow_label, node_label)}"
            )
            error_handler(error_msgs, msg, None, verbose)


class Actor:
    """
    The class which is used to process :py:class:`~dff.script.Context`
    according to the :py:class:`~dff.script.Script`.

    :param script: The dialog scenario: a graph described by the :py:class:`.Keywords`.
        While the graph is being initialized, it is validated and then used for the dialog.
    :param start_label: The start node of :py:class:`~dff.script.Script`. The execution begins with it.
    :param fallback_label: The label of :py:class:`~dff.script.Script`.
        Dialog comes into that label if all other transitions failed,
        or there was an error while executing the scenario.
        Defaults to `None`.
    :param label_priority: Default priority value for all :py:const:`labels <dff.script.NodeLabel3Type>`
        where there is no priority. Defaults to `1.0`.
    :param condition_handler: Handler that processes a call of condition functions. Defaults to `None`.
    :param handlers: This variable is responsible for the usage of external handlers on
        the certain stages of work of :py:class:`~dff.script.Actor`.

        - key (:py:class:`~dff.script.ActorStage`) - Stage in which the handler is called.
        - value (List[Callable]) - The list of called handlers for each stage.  Defaults to an empty `dict`.
    """

    def __init__(
        self,
        script: Union[Script, dict],
        start_label: NodeLabel2Type,
        fallback_label: Optional[NodeLabel2Type] = None,
        label_priority: float = 1.0,
        condition_handler: Optional[Callable] = None,
        handlers: Optional[Dict[ActorStage, List[Callable]]] = None,
    ):
        # script validation
        self.script = script if isinstance(script, Script) else Script(script=script)
        self.label_priority = label_priority

        # node labels validation
        self.start_label = normalize_label(start_label)
        if self.script.get(self.start_label[0], {}).get(self.start_label[1]) is None:
            raise ValueError(f"Unknown start_label={self.start_label}")

        if fallback_label is None:
            self.fallback_label = self.start_label
        else:
            self.fallback_label = normalize_label(fallback_label)
            if self.script.get(self.fallback_label[0], {}).get(self.fallback_label[1]) is None:
                raise ValueError(f"Unknown fallback_label={self.fallback_label}")
        self.condition_handler = default_condition_handler if condition_handler is None else condition_handler

        self.handlers = {} if handlers is None else handlers

        # NB! The following API is highly experimental and may be removed at ANY time WITHOUT FURTHER NOTICE!!
        self._clean_turn_cache = True

    def __call__(
        self, pipeline: Pipeline, ctx: Optional[Union[Context, dict, str]] = None, *args, **kwargs
    ) -> Union[Context, dict, str]:
        # context init
        ctx = self._context_init(ctx, *args, **kwargs)
        self._run_handlers(ctx, pipeline, ActorStage.CONTEXT_INIT, *args, **kwargs)

        # get previous node
        ctx = self._get_previous_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, pipeline, ActorStage.GET_PREVIOUS_NODE, *args, **kwargs)

        # rewrite previous node
        ctx = self._rewrite_previous_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, pipeline, ActorStage.REWRITE_PREVIOUS_NODE, *args, **kwargs)

        # run pre transitions processing
        ctx = self._run_pre_transitions_processing(ctx, pipeline, *args, **kwargs)
        self._run_handlers(ctx, pipeline, ActorStage.RUN_PRE_TRANSITIONS_PROCESSING, *args, **kwargs)

        # get true labels for scopes (GLOBAL, LOCAL, NODE)
        ctx = self._get_true_labels(ctx, pipeline, *args, **kwargs)
        self._run_handlers(ctx, pipeline, ActorStage.GET_TRUE_LABELS, *args, **kwargs)

        # get next node
        ctx = self._get_next_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, pipeline, ActorStage.GET_NEXT_NODE, *args, **kwargs)

        ctx.add_label(ctx.framework_states["actor"]["next_label"][:2])

        # rewrite next node
        ctx = self._rewrite_next_node(ctx, *args, **kwargs)
        self._run_handlers(ctx, pipeline, ActorStage.REWRITE_NEXT_NODE, *args, **kwargs)

        # run pre response processing
        ctx = self._run_pre_response_processing(ctx, pipeline, *args, **kwargs)
        self._run_handlers(ctx, pipeline, ActorStage.RUN_PRE_RESPONSE_PROCESSING, *args, **kwargs)

        # create response
        ctx.framework_states["actor"]["response"] = ctx.framework_states["actor"][
            "pre_response_processed_node"
        ].run_response(ctx, pipeline, *args, **kwargs)
        self._run_handlers(ctx, pipeline, ActorStage.CREATE_RESPONSE, *args, **kwargs)
        ctx.add_response(ctx.framework_states["actor"]["response"])

        self._run_handlers(ctx, pipeline, ActorStage.FINISH_TURN, *args, **kwargs)
        if self._clean_turn_cache:
            cache_clear()

        del ctx.framework_states["actor"]
        return ctx

    @staticmethod
    def _context_init(ctx: Optional[Union[Context, dict, str]] = None, *args, **kwargs) -> Context:
        ctx = Context.cast(ctx)
        if not ctx.requests:
            ctx.add_request(Message())
        ctx.framework_states["actor"] = {}
        return ctx

    def _get_previous_node(self, ctx: Context, *args, **kwargs) -> Context:
        ctx.framework_states["actor"]["previous_label"] = (
            normalize_label(ctx.last_label) if ctx.last_label else self.start_label
        )
        ctx.framework_states["actor"]["previous_node"] = self.script.get(
            ctx.framework_states["actor"]["previous_label"][0], {}
        ).get(ctx.framework_states["actor"]["previous_label"][1], Node())
        return ctx

    def _get_true_labels(self, ctx: Context, pipeline: Pipeline, *args, **kwargs) -> Context:
        # GLOBAL
        ctx.framework_states["actor"]["global_transitions"] = (
            self.script.get(GLOBAL, {}).get(GLOBAL, Node()).transitions
        )
        ctx.framework_states["actor"]["global_true_label"] = self._get_true_label(
            ctx.framework_states["actor"]["global_transitions"], ctx, pipeline, GLOBAL, "global"
        )

        # LOCAL
        ctx.framework_states["actor"]["local_transitions"] = (
            self.script.get(ctx.framework_states["actor"]["previous_label"][0], {}).get(LOCAL, Node()).transitions
        )
        ctx.framework_states["actor"]["local_true_label"] = self._get_true_label(
            ctx.framework_states["actor"]["local_transitions"],
            ctx,
            pipeline,
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
            pipeline,
            ctx.framework_states["actor"]["previous_label"][0],
            "node",
        )
        return ctx

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

    def _rewrite_previous_node(self, ctx: Context, *args, **kwargs) -> Context:
        node = ctx.framework_states["actor"]["previous_node"]
        flow_label = ctx.framework_states["actor"]["previous_label"][0]
        ctx.framework_states["actor"]["previous_node"] = self._overwrite_node(
            node,
            flow_label,
            only_current_node_transitions=True,
        )
        return ctx

    def _rewrite_next_node(self, ctx: Context, *args, **kwargs) -> Context:
        node = ctx.framework_states["actor"]["next_node"]
        flow_label = ctx.framework_states["actor"]["next_label"][0]
        ctx.framework_states["actor"]["next_node"] = self._overwrite_node(node, flow_label)
        return ctx

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

    def _run_pre_transitions_processing(self, ctx: Context, pipeline: Pipeline, *args, **kwargs) -> Context:
        ctx.framework_states["actor"]["processed_node"] = copy.deepcopy(ctx.framework_states["actor"]["previous_node"])
        ctx = ctx.framework_states["actor"]["previous_node"].run_pre_transitions_processing(
            ctx, pipeline, *args, **kwargs
        )
        ctx.framework_states["actor"]["pre_transitions_processed_node"] = ctx.framework_states["actor"][
            "processed_node"
        ]
        del ctx.framework_states["actor"]["processed_node"]
        return ctx

    def _run_pre_response_processing(self, ctx: Context, pipeline: Pipeline, *args, **kwargs) -> Context:
        ctx.framework_states["actor"]["processed_node"] = copy.deepcopy(ctx.framework_states["actor"]["next_node"])
        ctx = ctx.framework_states["actor"]["next_node"].run_pre_response_processing(ctx, pipeline, *args, **kwargs)
        ctx.framework_states["actor"]["pre_response_processed_node"] = ctx.framework_states["actor"]["processed_node"]
        del ctx.framework_states["actor"]["processed_node"]
        return ctx

    def _get_true_label(
        self,
        transitions: dict,
        ctx: Context,
        pipeline: Pipeline,
        flow_label: LabelType,
        transition_info: str = "",
        *args,
        **kwargs,
    ) -> Optional[NodeLabel3Type]:
        true_labels = []
        for label, condition in transitions.items():
            if self.condition_handler(condition, ctx, pipeline, *args, **kwargs):
                if callable(label):
                    label = label(ctx, pipeline, *args, **kwargs)
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

    def _run_handlers(self, ctx, pipeline: Pipeline, actor_stage: ActorStage, *args, **kwargs):
        [handler(ctx, pipeline, *args, **kwargs) for handler in self.handlers.get(actor_stage, [])]

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

    def validate_script(self, verbose: bool = True):
        # TODO: script has to not contain priority == -inf, because it uses for miss values
        error_msgs = []
        for flow_name, flow in self.script.items():
            for node_name, node in flow.items():
                # validate labeling
                for label in node.transitions.keys():
                    if callable(label):
                        validate_callable(label, "label", flow_name, node_name, error_msgs, verbose, [Context, Pipeline, Any, Any])
                    else:
                        norm_label = normalize_label(label, flow_name)
                        if norm_label is None:
                            msg = (
                                f"Label can not be normalized for label={label}, "
                                f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                            )
                            error_handler(error_msgs, msg, None, verbose)
                            continue
                        norm_fl, norm_nl, _ = norm_label
                        if norm_fl not in self.script.keys():
                            msg = (
                                f"Flow label {norm_fl} can not be found for label={label}, "
                                f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                            )
                        elif norm_nl not in flow.keys() or norm_nl not in self.script[norm_fl].keys():
                            msg = (
                                f"Node label {norm_nl} can not be found for label={label}, "
                                f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                            )
                        else:
                            msg = None
                        if msg is not None:
                            error_handler(error_msgs, msg, None, verbose)

                # validate responses
                if callable(node.response):
                    validate_callable(node.response, "response", flow_name, node_name, error_msgs, verbose, [Context, Pipeline, Any, Any], Message)
                elif node.response is not None and not issubclass(type(node.response), Message):
                    msg = (
                        f"Expected type of response is subclass of {Message}, got type(response)={type(node.response)}, "
                        f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                    )
                    error_handler(error_msgs, msg, None, verbose)

                # validate conditions
                for label, condition in node.transitions.items():
                    if callable(condition):
                        validate_callable(condition, "condition", flow_name, node_name, error_msgs, verbose, [Context, Pipeline, Any, Any], bool)
                    else:
                        msg = (
                            f"Expected type of condition for label={label} is {Callable}, "
                            f"got type(condition)={type(condition)}, "
                            f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                        )
                        error_handler(error_msgs, msg, None, verbose)

                # validate pre_transitions- and pre_response_processing
                for place, functions in zip(("transitions", "response"), (node.pre_transitions_processing, node.pre_response_processing)):
                    for name, function in functions.items():
                        if callable(function):
                            validate_callable(function, f"pre_{place}_processing {name}", flow_name, node_name, error_msgs, verbose, [Context, Pipeline, Any, Any], Context)
                        else:
                            msg = (
                                f"Expected type of pre_{place}_processing {name} is {Callable}, "
                                f"got type(pre_{place}_processing)={type(function)}, "
                                f"error was found in (flow_label, node_label)={(flow_name, node_name)}"
                            )
                            error_handler(error_msgs, msg, None, verbose)
        return error_msgs


def default_condition_handler(
    condition: Callable, ctx: Context, pipeline: Pipeline, *args, **kwargs
) -> Callable[[Context, Pipeline, Any, Any], bool]:
    """
    The simplest and quickest condition handler for trivial condition handling returns the callable condition:

    :param condition: Condition to copy.
    :param ctx: Context of current condition.
    :param pipeline: Pipeline we use in this condition.
    """
    return condition(ctx, pipeline, *args, **kwargs)
