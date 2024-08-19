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
from typing import Union, TYPE_CHECKING
from pydantic import Field, model_validator

from chatsky.core.service.component import PipelineComponent
from chatsky.core.node_label import AbsoluteNodeLabel, AbsoluteNodeLabelInitTypes
from chatsky.core.transition import get_next_label
from chatsky.core.message import Message

from chatsky.core.context import Context
from chatsky.core.script import Script
from chatsky.core.script_function import BaseProcessing

if TYPE_CHECKING:
    from chatsky.core.pipeline import Pipeline

logger = logging.getLogger(__name__)


class Actor(PipelineComponent):
    """
    The class which is used to process :py:class:`~chatsky.script.Context`
    according to the :py:class:`~chatsky.script.Script`.
    """

    script: Script
    """
    The dialog scenario: a graph described by the :py:class:`.Keywords`.
    While the graph is being initialized, it is validated and then used for the dialog.
    """
    fallback_label: AbsoluteNodeLabel
    """
    The label of :py:class:`~chatsky.script.Script`.
    Dialog comes into that label if all other transitions failed,
    or there was an error while executing the scenario. Defaults to `None`.
    """
    default_priority: float = 1.0
    """
    Default priority value for all :py:const:`labels <chatsky.script.ConstLabel>`
    where there is no priority. Defaults to `1.0`.
    """

    @model_validator(mode="after")
    def __tick_async_flag__(self):
        self.calculated_async_flag = False
        return self

    @model_validator(mode="after")
    def __fallback_label_validator__(self):
        """
        Validate :py:data:`~.Actor.fallback_label`.
        :raises ValueError: If `fallback_label` doesn't exist in the given :py:class:`~.Script`.
        """
        if self.script.get_node(self.fallback_label) is None:
            raise ValueError(f"Unknown fallback_label={self.fallback_label}")
        return self

    @property
    def computed_name(self) -> str:
        return "actor"

    async def run_component(self, ctx: Context, pipeline: Pipeline) -> None:
        next_label = self.fallback_label

        try:
            ctx.framework_data.current_node = self.script.get_global_local_inherited_node(ctx.last_label)

            logger.debug(f"Running pre_transition")
            await self._run_processing(ctx.current_node.pre_transition, ctx)

            logger.debug(f"Running transitions")

            destination_result = await get_next_label(ctx, ctx.current_node.transitions, self.default_priority)
            if destination_result is not None:
                next_label = destination_result
        except Exception as exc:
            logger.exception("Exception occurred during transition processing.", exc_info=exc)

        logger.debug(f"Next label: {next_label!r}")

        ctx.add_label(next_label)

        response = Message()

        try:
            ctx.framework_data.current_node = self.script.get_global_local_inherited_node(next_label)

            logger.debug(f"Running pre_response")
            await self._run_processing(ctx.current_node.pre_response, ctx)

            node_response = ctx.current_node.response
            if node_response is not None:
                response_result = await node_response(ctx)
                if isinstance(response_result, Message):
                    response = response_result
                else:
                    logger.debug("Response was not produced.")
            else:
                logger.debug("Node has empty response.")
        except Exception as exc:
            logger.exception("Exception occurred during response processing.", exc_info=exc)

        ctx.add_response(response)

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
