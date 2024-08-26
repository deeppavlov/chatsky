"""
Component
---------
The Component module defines a :py:class:`.PipelineComponent` class,
which is a fundamental building block of the framework. A PipelineComponent represents a single
step in a processing pipeline, and is responsible for performing a specific task or set of tasks.

The PipelineComponent class can be a group or a service. It is designed to be reusable and composable,
allowing developers to create complex processing pipelines by combining multiple components.
"""

from __future__ import annotations
import logging
import abc
import asyncio
from typing import Optional, Awaitable, TYPE_CHECKING
from pydantic import BaseModel, Field, model_validator

from chatsky.script import Context

from ..service.extra import BeforeHandler, AfterHandler
from ..conditions import always_start_condition
from ..types import (
    StartConditionCheckerFunction,
    ComponentExecutionState,
    ServiceRuntimeInfo,
    GlobalExtraHandlerType,
    ExtraHandlerFunction,
    ExtraHandlerType,
)
from ...utils.devel import wrap_sync_function_in_async

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from chatsky.pipeline.pipeline.pipeline import Pipeline


class PipelineComponent(abc.ABC, BaseModel, extra="forbid", arbitrary_types_allowed=True):
    """
    This class represents a pipeline component, which is a service or a service group.
    It contains some fields that they have in common.
    """

    before_handler: BeforeHandler = Field(default_factory=BeforeHandler)
    """
    :py:class:`~.BeforeHandler`, associated with this component.
    """
    after_handler: AfterHandler = Field(default_factory=AfterHandler)
    """
    :py:class:`~.AfterHandler`, associated with this component.
    """
    timeout: Optional[float] = None
    """
    (for asynchronous only!) Maximum component execution time (in seconds),
    if it exceeds this time, it is interrupted.
    """
    asynchronous: bool = False
    """
    Optional flag that indicates whether this component
    should be executed concurrently with adjacent async components.
    """
    start_condition: StartConditionCheckerFunction = Field(default=always_start_condition)
    """
    :py:class:`~.pipeline.types.StartConditionCheckerFunction` that is invoked before each component execution;
    component is executed only if it returns `True`.
    """
    name: Optional[str] = None
    """
    Component name (should be unique in single :py:class:`~.pipeline.service.group.ServiceGroup`),
    should not be blank or contain the ``.`` character.
    """
    path: Optional[str] = None
    """
    Separated by dots path to component, is universally unique.
    """

    @model_validator(mode="after")
    def __pipeline_component_validator__(self):
        """
        Validate this component.

        :raises ValueError: If component's name is blank or if it contains dots.
        :raises Exception: In case component can't be async, but was requested to be.
        """
        if self.name is not None:
            if self.name == "":
                raise ValueError("Name cannot be blank.")
            if "." in self.name:
                raise ValueError(f"Name cannot contain '.': {self.name!r}.")

        return self

    def _set_state(self, ctx: Context, value: ComponentExecutionState):
        """
        Method for component runtime state setting, state is preserved in `ctx.framework_data`.

        :param ctx: :py:class:`~.Context` to keep state in.
        :param value: State to set.
        :return: `None`
        """
        ctx.framework_data.service_states[self.path] = value

    def get_state(self, ctx: Context, default: Optional[ComponentExecutionState] = None) -> ComponentExecutionState:
        """
        Method for component runtime state getting, state is preserved in `ctx.framework_data`.

        :param ctx: :py:class:`~.Context` to get state from.
        :param default: Default to return if no record found
            (usually it's :py:attr:`~.pipeline.types.ComponentExecutionState.NOT_RUN`).
        :return: :py:class:`~pipeline.types.ComponentExecutionState` of this service or default if not found.
        """
        return ctx.framework_data.service_states.get(self.path, default if default is not None else None)

    async def run_extra_handler(self, stage: ExtraHandlerType, ctx: Context, pipeline: Pipeline):
        extra_handler = None
        if stage == ExtraHandlerType.BEFORE:
            extra_handler = self.before_handler
        if stage == ExtraHandlerType.AFTER:
            extra_handler = self.after_handler
        if extra_handler is None:
            return
        try:
            extra_handler_result = await extra_handler(ctx, pipeline, self._get_runtime_info(ctx))
            if extra_handler.asynchronous and isinstance(extra_handler_result, Awaitable):
                await extra_handler_result
        except asyncio.TimeoutError:
            logger.warning(f"{type(self).__name__} '{self.name}' {extra_handler.stage} extra handler timed out!")

    @abc.abstractmethod
    async def run_component(self, ctx: Context, pipeline: Pipeline) -> Optional[ComponentExecutionState]:
        """
        Run this component.

        :param ctx: Current dialog :py:class:`~.Context`.
        :param pipeline: This :py:class:`~.Pipeline`.
        """
        raise NotImplementedError

    @property
    def computed_name(self) -> str:
        """
        Default name that is used if :py:attr:`~.PipelineComponent.name` is not defined.
        In case two components in a :py:class:`~.ServiceGroup` have the same
        :py:attr:`~.PipelineComponent.computed_name` an incrementing number is appended to the name.
        """
        return "noname_service"

    async def _run(self, ctx: Context, pipeline: Pipeline) -> None:
        """
        A method for running a pipeline component. Executes extra handlers before and after execution,
        launches `run_component` method. This method is run after the component's timeout is set (if needed).

        :param ctx: Current dialog :py:class:`~.Context`.
        :param pipeline: This :py:class:`~.Pipeline`.
        """
        try:
            if await wrap_sync_function_in_async(self.start_condition, ctx, pipeline):
                await self.run_extra_handler(ExtraHandlerType.BEFORE, ctx, pipeline)

                self._set_state(ctx, ComponentExecutionState.RUNNING)
                if await self.run_component(ctx, pipeline) is not ComponentExecutionState.FAILED:
                    self._set_state(ctx, ComponentExecutionState.FINISHED)

                await self.run_extra_handler(ExtraHandlerType.AFTER, ctx, pipeline)
            else:
                self._set_state(ctx, ComponentExecutionState.NOT_RUN)
        except Exception as exc:
            self._set_state(ctx, ComponentExecutionState.FAILED)
            logger.error(f"Service '{self.name}' execution failed!", exc_info=exc)

    async def __call__(self, ctx: Context, pipeline: Pipeline) -> Optional[Awaitable]:
        """
        A method for calling pipeline components.
        It sets up timeout if this component is asynchronous and executes it using :py:meth:`~._run` method.

        :param ctx: Current dialog :py:class:`~.Context`.
        :param pipeline: This :py:class:`~.Pipeline`.
        :return: `None` if the service is synchronous; an `Awaitable` otherwise.
        """
        if self.asynchronous:
            task = asyncio.create_task(self._run(ctx, pipeline))
            return asyncio.wait_for(task, timeout=self.timeout)
        else:
            return await self._run(ctx, pipeline)

    def add_extra_handler(self, global_extra_handler_type: GlobalExtraHandlerType, extra_handler: ExtraHandlerFunction):
        """
        Method for adding a global extra handler to this particular component.

        :param global_extra_handler_type: A type of extra handler to add.
        :param extra_handler: A :py:class:`~.GlobalExtraHandlerType` to add to the component as an extra handler.
        :type extra_handler: :py:data:`~.ExtraHandlerFunction`
        :return: `None`
        """
        target = (
            self.before_handler if global_extra_handler_type is GlobalExtraHandlerType.BEFORE else self.after_handler
        )
        target.functions.append(extra_handler)

    def _get_runtime_info(self, ctx: Context) -> ServiceRuntimeInfo:
        """
        Method for retrieving runtime info about this component.

        :param ctx: Current dialog :py:class:`~.Context`.
        :return: :py:class:`~.chatsky.script.typing.ServiceRuntimeInfo`
            object where all not set fields are replaced with `[None]`.
        """
        return ServiceRuntimeInfo(
            name=self.name if self.name is not None else "[None]",
            path=self.path if self.path is not None else "[None]",
            timeout=self.timeout,
            asynchronous=self.asynchronous,
            execution_state=ctx.framework_data.service_states.copy(),
        )

    @property
    def info_dict(self) -> dict:
        """
        Property for retrieving info dictionary about this component.
        All not set fields there are replaced with `[None]`.

        :return: Info dict, containing most important component public fields as well as its type.
        """
        return {
            "type": type(self).__name__,
            "name": self.name,
            "path": self.path if self.path is not None else "[None]",
            "asynchronous": self.asynchronous,
            "start_condition": self.start_condition.__name__,
            "extra_handlers": {
                "before": self.before_handler.info_dict,
                "after": self.after_handler.info_dict,
            },
        }
