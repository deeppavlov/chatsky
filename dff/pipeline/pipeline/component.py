"""
Component
---------
The Component module defines a :py:class:`.PipelineComponent` class,
which is a fundamental building block of the framework. A PipelineComponent represents a single
step in a processing pipeline, and is responsible for performing a specific task or set of tasks.

The PipelineComponent class can be a group or a service. It is designed to be reusable and composable,
allowing developers to create complex processing pipelines by combining multiple components.
"""
import logging
import abc
import asyncio
import copy
from typing import Optional, Union, Awaitable, ForwardRef

from dff.script import Context

from ..service.extra import BeforeHandler, AfterHandler
from ..conditions import always_start_condition
from ..types import (
    PIPELINE_STATE_KEY,
    StartConditionCheckerFunction,
    ComponentExecutionState,
    ServiceRuntimeInfo,
    GlobalExtraHandlerType,
    ExtraHandlerFunction,
    ExtraHandlerType,
    ExtraHandlerBuilder,
)

logger = logging.getLogger(__name__)

Pipeline = ForwardRef("Pipeline")


class PipelineComponent(abc.ABC):
    """
    This class represents a pipeline component, which is a service or a service group.
    It contains some fields that they have in common.

    :param before_handler: :py:class:`~.BeforeHandler`, associated with this component.
    :type before_handler: Optional[:py:data:`~.ExtraHandlerBuilder`]
    :param after_handler: :py:class:`~.AfterHandler`, associated with this component.
    :type after_handler: Optional[:py:data:`~.ExtraHandlerBuilder`]
    :param timeout: (for asynchronous only!) Maximum component execution time (in seconds),
        if it exceeds this time, it is interrupted.
    :param requested_async_flag: Requested asynchronous property;
        if not defined, `calculated_async_flag` is used instead.
    :param calculated_async_flag: Whether the component can be asynchronous or not
        1) for :py:class:`~.pipeline.service.service.Service`: whether its `handler` is asynchronous or not,
        2) for :py:class:`~.pipeline.service.group.ServiceGroup`: whether all its `services` are asynchronous or not.

    :param start_condition: StartConditionCheckerFunction that is invoked before each component execution;
        component is executed only if it returns `True`.
    :type start_condition: Optional[:py:data:`~.StartConditionCheckerFunction`]
    :param name: Component name (should be unique in single :py:class:`~.pipeline.service.group.ServiceGroup`),
        should not be blank or contain `.` symbol.
    :param path: Separated by dots path to component, is universally unique.
    """

    def __init__(
        self,
        before_handler: Optional[ExtraHandlerBuilder] = None,
        after_handler: Optional[ExtraHandlerBuilder] = None,
        timeout: Optional[float] = None,
        requested_async_flag: Optional[bool] = None,
        calculated_async_flag: bool = False,
        start_condition: Optional[StartConditionCheckerFunction] = None,
        name: Optional[str] = None,
        path: Optional[str] = None,
    ):
        self.timeout = timeout
        """
        Maximum component execution time (in seconds),
        if it exceeds this time, it is interrupted (for asynchronous only!).
        """
        self.requested_async_flag = requested_async_flag
        """Requested asynchronous property; if not defined, :py:attr:`~requested_async_flag` is used instead."""
        self.calculated_async_flag = calculated_async_flag
        """Calculated asynchronous property, whether the component can be asynchronous or not."""
        self.start_condition = always_start_condition if start_condition is None else start_condition
        """
        Component start condition that is invoked before each component execution;
        component is executed only if it returns `True`.
        """
        self.name = name
        """
        Component name (should be unique in single :py:class:`~pipeline.service.group.ServiceGroup`),
        should not be blank or contain '.' symbol.
        """
        self.path = path
        """
        Dot-separated path to component (is universally unique).
        This attribute is set in :py:func:`~dff.pipeline.pipeline.utils.finalize_service_group`.
        """

        self.before_handler = BeforeHandler([] if before_handler is None else before_handler)
        self.after_handler = AfterHandler([] if after_handler is None else after_handler)

        if name is not None and (name == "" or "." in name):
            raise Exception(f"User defined service name shouldn't be blank or contain '.' (service: {name})!")

        if not calculated_async_flag and requested_async_flag:
            raise Exception(f"{type(self).__name__} '{name}' can't be asynchronous!")

    def _set_state(self, ctx: Context, value: ComponentExecutionState):
        """
        Method for component runtime state setting, state is preserved in `ctx.framework_states` dict,
        in subdict, dedicated to this library.

        :param ctx: :py:class:`~.Context` to keep state in.
        :param value: State to set.
        :return: `None`
        """
        if PIPELINE_STATE_KEY not in ctx.framework_states:
            ctx.framework_states[PIPELINE_STATE_KEY] = {}
        ctx.framework_states[PIPELINE_STATE_KEY][self.path] = value

    def get_state(self, ctx: Context, default: Optional[ComponentExecutionState] = None) -> ComponentExecutionState:
        """
        Method for component runtime state getting, state is preserved in `ctx.framework_states` dict,
        in subdict, dedicated to this library.

        :param ctx: :py:class:`~.Context` to get state from.
        :param default: Default to return if no record found
            (usually it's :py:attr:`~.pipeline.types.ComponentExecutionState.NOT_RUN`).
        :return: :py:class:`~pipeline.types.ComponentExecutionState` of this service or default if not found.
        """
        return ctx.framework_states[PIPELINE_STATE_KEY].get(self.path, default if default is not None else None)

    @property
    def asynchronous(self) -> bool:
        """
        Property, that indicates, whether this component is synchronous or asynchronous.
        It is calculated according to the following rules:

        - | If component **can** be asynchronous and :py:attr:`~requested_async_flag` is set,
            it returns :py:attr:`~requested_async_flag`.
        - | If component **can** be asynchronous and :py:attr:`~requested_async_flag` isn't set,
            it returns `True`.
        - | If component **can't** be asynchronous and :py:attr:`~requested_async_flag` is `False` or not set,
            it returns `False`.
        - | If component **can't** be asynchronous and :py:attr:`~requested_async_flag` is `True`,
            an Exception is thrown in constructor.

        """
        return self.calculated_async_flag if self.requested_async_flag is None else self.requested_async_flag

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
    async def _run(self, ctx: Context, pipeline: Optional[Pipeline] = None) -> Optional[Context]:
        """
        A method for running pipeline component, it is overridden in all its children.
        This method is run after the component's timeout is set (if needed).

        :param ctx: Current dialog :py:class:`~.Context`.
        :param pipeline: This :py:class:`~.Pipeline`.
        :return: :py:class:`~.Context` if this is a synchronous service or `None`,
            asynchronous services shouldn't modify :py:class:`~.Context`.
        """
        raise NotImplementedError

    async def __call__(self, ctx: Context, pipeline: Optional[Pipeline] = None) -> Optional[Union[Context, Awaitable]]:
        """
        A method for calling pipeline components.
        It sets up timeout if this component is asynchronous and executes it using :py:meth:`~._run` method.

        :param ctx: Current dialog :py:class:`~.Context`.
        :param pipeline: This :py:class:`~.Pipeline`.
        :return: :py:class:`~.Context` if this is a synchronous service or :py:class:`~.typing.const.Awaitable`,
            asynchronous services shouldn't modify :py:class:`~.Context`.
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
        :return: :py:class:`~.dff.script.typing.ServiceRuntimeInfo`
            object where all not set fields are replaced with `[None]`.
        """
        return ServiceRuntimeInfo(
            name=self.name if self.name is not None else "[None]",
            path=self.path if self.path is not None else "[None]",
            timeout=self.timeout,
            asynchronous=self.asynchronous,
            execution_state=copy.deepcopy(ctx.framework_states[PIPELINE_STATE_KEY]),
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
