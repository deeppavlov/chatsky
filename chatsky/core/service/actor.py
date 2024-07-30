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

.. figure:: /_static/drawio/core/user_actor.png
"""

from __future__ import annotations
import logging
import asyncio
from typing import Union, Optional

from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.transition import Transition
from chatsky.utils.turn_caching import cache_clear
from chatsky.core.message import Message

from chatsky.core.context import Context
from chatsky.core.script import Script
from chatsky.core.script_function import BaseProcessing

logger = logging.getLogger(__name__)


class Actor:
    """
    The class which is used to process :py:class:`~chatsky.script.Context`
    according to the :py:class:`~chatsky.script.Script`.

    :param script: The dialog scenario: a graph described by the :py:class:`.Keywords`.
        While the graph is being initialized, it is validated and then used for the dialog.
    :param start_label: The start node of :py:class:`~chatsky.script.Script`. The execution begins with it.
    :param fallback_label: The label of :py:class:`~chatsky.script.Script`.
        Dialog comes into that label if all other transitions failed,
        or there was an error while executing the scenario.
        Defaults to `None`.
    :param label_priority: Default priority value for all :py:const:`labels <chatsky.script.ConstLabel>`
        where there is no priority. Defaults to `1.0`.
    :param condition_handler: Handler that processes a call of condition functions. Defaults to `None`.
    :param handlers: This variable is responsible for the usage of external handlers on
        the certain stages of work of :py:class:`~chatsky.script.Actor`.

        - key (:py:class:`~chatsky.script.ActorStage`) - Stage in which the handler is called.
        - value (List[Callable]) - The list of called handlers for each stage.  Defaults to an empty `dict`.
    """

    def __init__(
        self,
        script: Union[Script, dict],
        start_label: AbsoluteNodeLabel,
        fallback_label: Optional[AbsoluteNodeLabel] = None,
        default_priority: float = 1.0,
    ):
        self.script = Script.model_validate(script)
        self.default_priority = default_priority

        self.start_label = AbsoluteNodeLabel.model_validate(start_label)
        if self.script.get_node(self.start_label) is None:
            raise ValueError(f"Unknown start_label={self.start_label}")

        if fallback_label is None:
            self.fallback_label = self.start_label
        else:
            self.fallback_label = AbsoluteNodeLabel.model_validate(fallback_label)
            if self.script.get_node(self.fallback_label) is None:
                raise ValueError(f"Unknown fallback_label={self.fallback_label}")

        # NB! The following API is highly experimental and may be removed at ANY time WITHOUT FURTHER NOTICE!!
        self._clean_turn_cache = True

    async def __call__(self, ctx: Context):
        ctx.framework_data.current_node = ctx._get_current_node().inherited_node  # todo: catch this

        logger.debug(f"Running pre_transition")
        await self._run_processing(ctx.current_node.pre_transition, ctx)

        logger.debug(f"Running transitions")
        transition_results = await asyncio.gather(
            *[transition.wrapped_call(ctx) for transition in ctx.current_node.transitions]
        )

        def transition_key(tr: Transition):
            priority = tr.priority
            if priority is None:
                return ctx.pipeline.actor.default_priority
            return priority

        transitions = sorted(
            [transition for transition in transition_results if isinstance(transition, Transition)],
            key=transition_key,
            reverse=True
        )

        if len(transitions) == 0:
            next_node = self.fallback_label
        else:
            next_node = transitions[0].dst
        logger.debug(f"Possible transitions: {transitions!r}")
        logger.debug(f"Next label: {next_node!r}")

        ctx.add_label(next_node)

        ctx.framework_data.current_node = ctx._get_current_node().inherited_node

        # run pre response processing
        await self._run_processing(ctx.current_node.pre_response, ctx)

        response = None

        node_response = ctx.current_node.response
        if node_response is not None:
            result = await node_response.wrapped_call(ctx)
            if isinstance(result, Message):
                response = result

        if response is None:
            logger.debug("Response was not produced")
            ctx.add_response(Message())
        else:
            logger.debug(f"Got response: {response!r}")
            ctx.add_response(response)

        if self._clean_turn_cache:
            cache_clear()

    @staticmethod
    async def _run_processing_parallel(processing: dict[str, BaseProcessing], ctx: Context) -> None:
        """
        Execute the processing functions for a particular node simultaneously,
        independent of the order.

        Picked depending on the value of the :py:class:`.Pipeline`'s `parallelize_processing` flag.
        """
        await asyncio.gather(
            *[func.wrapped_call(ctx, info=f"processing_name={name!r}") for name, func in processing.items()]
        )

    @staticmethod
    async def _run_processing_sequential(processing: dict[str, BaseProcessing], ctx: Context) -> None:
        """
        Execute the processing functions for a particular node in-order.

        Picked depending on the value of the :py:class:`.Pipeline`'s `parallelize_processing` flag.
        """
        for name, func in processing.items():
            await func.wrapped_call(ctx, info=f"processing_name={name!r}")

    @staticmethod
    async def _run_processing(processing: dict[str, BaseProcessing], ctx: Context) -> None:
        """
        Run `PRE_TRANSITIONS_PROCESSING` functions for a particular node.
        Pre-transition processing functions can modify the context state
        before the direction of the next transition is determined depending on that state.

        The execution order depends on the value of the :py:class:`.Pipeline`'s
        `parallelize_processing` flag.
        """
        if ctx.pipeline.parallelize_processing:
            await Actor._run_processing_parallel(processing, ctx)
        else:
            await Actor._run_processing_sequential(processing, ctx)
