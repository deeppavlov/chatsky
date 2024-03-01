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

from __future__ import annotations
import logging
import asyncio
from typing import Union, Callable, Optional, Dict, List, TYPE_CHECKING
import copy

from dff.utils.turn_caching import cache_clear
from dff.script.core.types import ActorStage, NodeLabel2Type, NodeLabel3Type, LabelType
from dff.script.core.message import Message

from dff.script.core.context import Context
from dff.script.core.script import Script, Node
from dff.script.core.normalization import normalize_label, normalize_response
from dff.script.core.keywords import GLOBAL, LOCAL
from dff.pipeline.service.utils import wrap_sync_function_in_async

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from dff.pipeline.pipeline.pipeline import Pipeline


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

    async def __call__(self, pipeline: Pipeline, ctx: Context):
        # context init
        self._context_init(ctx)
        await self._run_handlers(ctx, pipeline, ActorStage.CONTEXT_INIT)

        # get previous node
        self._get_previous_node(ctx)
        await self._run_handlers(ctx, pipeline, ActorStage.GET_PREVIOUS_NODE)

        # rewrite previous node
        self._rewrite_previous_node(ctx)
        await self._run_handlers(ctx, pipeline, ActorStage.REWRITE_PREVIOUS_NODE)

        # run pre transitions processing
        await self._run_pre_transitions_processing(ctx, pipeline)
        await self._run_handlers(ctx, pipeline, ActorStage.RUN_PRE_TRANSITIONS_PROCESSING)

        # get true labels for scopes (GLOBAL, LOCAL, NODE)
        await self._get_true_labels(ctx, pipeline)
        await self._run_handlers(ctx, pipeline, ActorStage.GET_TRUE_LABELS)

        # get next node
        self._get_next_node(ctx)
        await self._run_handlers(ctx, pipeline, ActorStage.GET_NEXT_NODE)

        ctx.add_label(ctx.framework_states["actor"]["next_label"][:2])

        # rewrite next node
        self._rewrite_next_node(ctx)
        await self._run_handlers(ctx, pipeline, ActorStage.REWRITE_NEXT_NODE)

        # run pre response processing
        await self._run_pre_response_processing(ctx, pipeline)
        await self._run_handlers(ctx, pipeline, ActorStage.RUN_PRE_RESPONSE_PROCESSING)

        # create response
        ctx.framework_states["actor"]["response"] = await self.run_response(
            ctx.framework_states["actor"]["pre_response_processed_node"].response, ctx, pipeline
        )
        await self._run_handlers(ctx, pipeline, ActorStage.CREATE_RESPONSE)
        ctx.add_response(ctx.framework_states["actor"]["response"])

        await self._run_handlers(ctx, pipeline, ActorStage.FINISH_TURN)
        if self._clean_turn_cache:
            cache_clear()

        del ctx.framework_states["actor"]

    @staticmethod
    def _context_init(ctx: Optional[Union[Context, dict, str]] = None):
        ctx.framework_states["actor"] = {}

    def _get_previous_node(self, ctx: Context):
        ctx.framework_states["actor"]["previous_label"] = (
            normalize_label(ctx.last_label) if ctx.last_label else self.start_label
        )
        ctx.framework_states["actor"]["previous_node"] = self.script.get(
            ctx.framework_states["actor"]["previous_label"][0], {}
        ).get(ctx.framework_states["actor"]["previous_label"][1], Node())

    async def _get_true_labels(self, ctx: Context, pipeline: Pipeline):
        # GLOBAL
        ctx.framework_states["actor"]["global_transitions"] = (
            self.script.get(GLOBAL, {}).get(GLOBAL, Node()).transitions
        )
        ctx.framework_states["actor"]["global_true_label"] = await self._get_true_label(
            ctx.framework_states["actor"]["global_transitions"], ctx, pipeline, GLOBAL, "global"
        )

        # LOCAL
        ctx.framework_states["actor"]["local_transitions"] = (
            self.script.get(ctx.framework_states["actor"]["previous_label"][0], {}).get(LOCAL, Node()).transitions
        )
        ctx.framework_states["actor"]["local_true_label"] = await self._get_true_label(
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
        ctx.framework_states["actor"]["node_true_label"] = await self._get_true_label(
            ctx.framework_states["actor"]["node_transitions"],
            ctx,
            pipeline,
            ctx.framework_states["actor"]["previous_label"][0],
            "node",
        )

    def _get_next_node(self, ctx: Context):
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

    def _rewrite_previous_node(self, ctx: Context):
        node = ctx.framework_states["actor"]["previous_node"]
        flow_label = ctx.framework_states["actor"]["previous_label"][0]
        ctx.framework_states["actor"]["previous_node"] = self._overwrite_node(
            node,
            flow_label,
            only_current_node_transitions=True,
        )

    def _rewrite_next_node(self, ctx: Context):
        node = ctx.framework_states["actor"]["next_node"]
        flow_label = ctx.framework_states["actor"]["next_label"][0]
        ctx.framework_states["actor"]["next_node"] = self._overwrite_node(node, flow_label)

    def _overwrite_node(
        self,
        current_node: Node,
        flow_label: LabelType,
        only_current_node_transitions: bool = False,
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

    async def run_response(
        self,
        response: Optional[Union[Message, Callable[..., Message]]],
        ctx: Context,
        pipeline: Pipeline,
    ) -> Message:
        """
        Executes the normalized response as an asynchronous function.
        See the details in the :py:func:`~normalize_response` function of `normalization.py`.
        """
        response = normalize_response(response)
        return await wrap_sync_function_in_async(response, ctx, pipeline)

    async def _run_processing_parallel(self, processing: dict, ctx: Context, pipeline: Pipeline) -> None:
        """
        Execute the processing functions for a particular node simultaneously,
        independent of the order.

        Picked depending on the value of the :py:class:`.Pipeline`'s `parallelize_processing` flag.
        """
        results = await asyncio.gather(
            *[wrap_sync_function_in_async(func, ctx, pipeline) for func in processing.values()],
            return_exceptions=True,
        )
        for exc, (processing_name, processing_func) in zip(results, processing.items()):
            if isinstance(exc, Exception):
                logger.error(
                    f"Exception {exc} for processing_name={processing_name} and processing_func={processing_func}",
                    exc_info=exc,
                )

    async def _run_processing_sequential(self, processing: dict, ctx: Context, pipeline: Pipeline) -> None:
        """
        Execute the processing functions for a particular node in-order.

        Picked depending on the value of the :py:class:`.Pipeline`'s `parallelize_processing` flag.
        """
        for processing_name, processing_func in processing.items():
            try:
                await wrap_sync_function_in_async(processing_func, ctx, pipeline)
            except Exception as exc:
                logger.error(
                    f"Exception {exc} for processing_name={processing_name} and processing_func={processing_func}",
                    exc_info=exc,
                )

    async def _run_pre_transitions_processing(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        Run `PRE_TRANSITIONS_PROCESSING` functions for a particular node.
        Pre-transition processing functions can modify the context state
        before the direction of the next transition is determined depending on that state.

        The execution order depends on the value of the :py:class:`.Pipeline`'s
        `parallelize_processing` flag.
        """
        ctx.framework_states["actor"]["processed_node"] = copy.deepcopy(ctx.framework_states["actor"]["previous_node"])
        pre_transitions_processing = ctx.framework_states["actor"]["previous_node"].pre_transitions_processing

        if pipeline.parallelize_processing:
            await self._run_processing_parallel(pre_transitions_processing, ctx, pipeline)
        else:
            await self._run_processing_sequential(pre_transitions_processing, ctx, pipeline)

        ctx.framework_states["actor"]["pre_transitions_processed_node"] = ctx.framework_states["actor"][
            "processed_node"
        ]
        del ctx.framework_states["actor"]["processed_node"]

    async def _run_pre_response_processing(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        Run `PRE_RESPONSE_PROCESSING` functions for a particular node.
        Pre-response processing functions can modify the response before it is
        returned to the user.

        The execution order depends on the value of the :py:class:`.Pipeline`'s
        `parallelize_processing` flag.
        """
        ctx.framework_states["actor"]["processed_node"] = copy.deepcopy(ctx.framework_states["actor"]["next_node"])
        pre_response_processing = ctx.framework_states["actor"]["next_node"].pre_response_processing

        if pipeline.parallelize_processing:
            await self._run_processing_parallel(pre_response_processing, ctx, pipeline)
        else:
            await self._run_processing_sequential(pre_response_processing, ctx, pipeline)

        ctx.framework_states["actor"]["pre_response_processed_node"] = ctx.framework_states["actor"]["processed_node"]
        del ctx.framework_states["actor"]["processed_node"]

    async def _get_true_label(
        self,
        transitions: dict,
        ctx: Context,
        pipeline: Pipeline,
        flow_label: LabelType,
        transition_info: str = "",
    ) -> Optional[NodeLabel3Type]:
        true_labels = []

        cond_booleans = await asyncio.gather(
            *(self.condition_handler(condition, ctx, pipeline) for condition in transitions.values())
        )
        for label, cond_is_true in zip(transitions.keys(), cond_booleans):
            if cond_is_true:
                if callable(label):
                    label = await wrap_sync_function_in_async(label, ctx, pipeline)
                    # TODO: explicit handling of errors
                    if label is None:
                        continue
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

    async def _run_handlers(self, ctx, pipeline: Pipeline, actor_stage: ActorStage):
        stage_handlers = self.handlers.get(actor_stage, [])
        async_handlers = [wrap_sync_function_in_async(handler, ctx, pipeline) for handler in stage_handlers]
        await asyncio.gather(*async_handlers)

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

    def validate_script(self, pipeline: Pipeline, verbose: bool = True):
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
            if not callable(label):
                label = normalize_label(label, flow_label)

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
        return error_msgs


async def default_condition_handler(
    condition: Callable, ctx: Context, pipeline: Pipeline
) -> Callable[[Context, Pipeline], bool]:
    """
    The simplest and quickest condition handler for trivial condition handling returns the callable condition:

    :param condition: Condition to copy.
    :param ctx: Context of current condition.
    :param pipeline: Pipeline we use in this condition.
    """
    return await wrap_sync_function_in_async(condition, ctx, pipeline)
