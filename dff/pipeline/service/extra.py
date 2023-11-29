"""
Extra Handler
-------------
The Extra Handler module contains additional functionality that extends the capabilities of the system
beyond the core functionality. Extra handlers is an input converting addition to :py:class:`.PipelineComponent`.
For example, it is used to grep statistics from components, timing, logging, etc.
"""
import asyncio
import logging
import inspect
from typing import Optional, List, ForwardRef

from dff.script import Context

from .utils import collect_defined_constructor_parameters_to_dict, _get_attrs_with_updates, wrap_sync_function_in_async
from ..types import (
    ServiceRuntimeInfo,
    ExtraHandlerType,
    ExtraHandlerBuilder,
    ExtraHandlerFunction,
    ExtraHandlerRuntimeInfo,
)

logger = logging.getLogger(__name__)

Pipeline = ForwardRef("Pipeline")


class _ComponentExtraHandler:
    """
    Class, representing an extra pipeline component handler.
    A component extra handler is a set of functions, attached to pipeline component (before or after it).
    Extra handlers should execute supportive tasks (like time or resources measurement, minor data transformations).
    Extra handlers should NOT edit context or pipeline, use services for that purpose instead.

    :param functions: An `ExtraHandlerBuilder` object, an `_ComponentExtraHandler` instance,
        a dict or a list of :py:data:`~.ExtraHandlerFunction`.
    :type functions: :py:data:`~.ExtraHandlerBuilder`
    :param stage: An :py:class:`~.ExtraHandlerType`, specifying whether this handler will be executed before or
        after pipeline component.
    :param timeout: (for asynchronous only!) Maximum component execution time (in seconds),
        if it exceeds this time, it is interrupted.
    :param asynchronous: Requested asynchronous property.
    """

    def __init__(
        self,
        functions: ExtraHandlerBuilder,
        stage: ExtraHandlerType = ExtraHandlerType.UNDEFINED,
        timeout: Optional[float] = None,
        asynchronous: Optional[bool] = None,
    ):
        overridden_parameters = collect_defined_constructor_parameters_to_dict(
            timeout=timeout, asynchronous=asynchronous
        )
        if isinstance(functions, _ComponentExtraHandler):
            self.__init__(
                **_get_attrs_with_updates(
                    functions,
                    ("calculated_async_flag", "stage"),
                    {"requested_async_flag": "asynchronous"},
                    overridden_parameters,
                )
            )
        elif isinstance(functions, dict):
            functions.update(overridden_parameters)
            self.__init__(**functions)
        elif isinstance(functions, List):
            self.functions = functions
            self.timeout = timeout
            self.requested_async_flag = asynchronous
            self.calculated_async_flag = all([asyncio.iscoroutinefunction(func) for func in self.functions])
            self.stage = stage
        else:
            raise Exception(f"Unknown type for {type(self).__name__} {functions}")

    @property
    def asynchronous(self) -> bool:
        """
        Property, that indicates, whether this component extra handler is synchronous or asynchronous.
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

    async def _run_function(
        self, func: ExtraHandlerFunction, ctx: Context, pipeline: Pipeline, component_info: ServiceRuntimeInfo
    ):
        handler_params = len(inspect.signature(func).parameters)
        if handler_params == 1:
            await wrap_sync_function_in_async(func, ctx)
        elif handler_params == 2:
            await wrap_sync_function_in_async(func, ctx, pipeline)
        elif handler_params == 3:
            extra_handler_runtime_info = ExtraHandlerRuntimeInfo(func=func, stage=self.stage, component=component_info)
            await wrap_sync_function_in_async(func, ctx, pipeline, extra_handler_runtime_info)
        else:
            raise Exception(
                f"Too many parameters required for component {component_info.name} {self.stage}"
                f" wrapper handler '{func.__name__}': {handler_params}!"
            )

    async def _run(self, ctx: Context, pipeline: Pipeline, component_info: ServiceRuntimeInfo):
        """
        Method for executing one of the wrapper functions (before or after).
        If the function is not set, nothing happens.

        :param stage: current `WrapperStage` (before or after).
        :param ctx: current dialog context.
        :param pipeline: the current pipeline.
        :param component_info: associated component's info dictionary.
        :return: `None`
        """

        if self.asynchronous:
            futures = [self._run_function(func, ctx, pipeline, component_info) for func in self.functions]
            for func, future in zip(self.functions, asyncio.as_completed(futures)):
                try:
                    await future
                except asyncio.TimeoutError:
                    logger.warning(f"Component {component_info.name} {self.stage} wrapper '{func.__name__}' timed out!")

        else:
            for func in self.functions:
                await self._run_function(func, ctx, pipeline, component_info)

    async def __call__(self, ctx: Context, pipeline: Pipeline, component_info: ServiceRuntimeInfo):
        """
        A method for calling pipeline components.
        It sets up timeout if this component is asynchronous and executes it using `_run` method.

        :param ctx: (required) Current dialog `Context`.
        :param pipeline: This `Pipeline`.
        :return: `Context` if this is a synchronous service or
            `Awaitable` if this is an asynchronous component or `None`.
        """
        if self.asynchronous:
            task = asyncio.create_task(self._run(ctx, pipeline, component_info))
            return await asyncio.wait_for(task, timeout=self.timeout)
        else:
            return await self._run(ctx, pipeline, component_info)

    @property
    def info_dict(self) -> dict:
        """
        Property for retrieving info dictionary about this wrapper.

        :return: Info dict, containing its fields as well as its type.
            All not set fields there are replaced with `None`.
        """
        return {
            "type": type(self).__name__,
            "timeout": self.timeout,
            "asynchronous": self.asynchronous,
            "functions": [func.__name__ for func in self.functions],
        }


class BeforeHandler(_ComponentExtraHandler):
    """
    A handler for extra functions that are executed before the component's main function.

    :param functions: A callable or a list of callables that will be executed
        before the component's main function.
    :type functions: ExtraHandlerBuilder
    :param timeout: Optional timeout for the execution of the extra functions, in
        seconds.
    :param asynchronous: Optional flag that indicates whether the extra functions
        should be executed asynchronously. The default value of the flag is True
        if all the functions in this handler are asynchronous.
    """

    def __init__(
        self,
        functions: ExtraHandlerBuilder,
        timeout: Optional[int] = None,
        asynchronous: Optional[bool] = None,
    ):
        super().__init__(functions, ExtraHandlerType.BEFORE, timeout, asynchronous)


class AfterHandler(_ComponentExtraHandler):
    """
    A handler for extra functions that are executed after the component's main function.

    :param functions: A callable or a list of callables that will be executed
        after the component's main function.
    :type functions: ExtraHandlerBuilder
    :param timeout: Optional timeout for the execution of the extra functions, in
        seconds.
    :param asynchronous: Optional flag that indicates whether the extra functions
        should be executed asynchronously. The default value of the flag is True
        if all the functions in this handler are asynchronous.
    """

    def __init__(
        self,
        functions: ExtraHandlerBuilder,
        timeout: Optional[int] = None,
        asynchronous: Optional[bool] = None,
    ):
        super().__init__(functions, ExtraHandlerType.AFTER, timeout, asynchronous)
