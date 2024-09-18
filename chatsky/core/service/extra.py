"""
Extra Handler
-------------
Extra handlers are functions that are executed before or after a
:py:class:`~chatsky.core.service.component.PipelineComponent`.
"""

from __future__ import annotations
import asyncio
import logging
import inspect
from typing import Optional, List, TYPE_CHECKING, Any, ClassVar, Union, Callable
from typing_extensions import Annotated, TypeAlias
from pydantic import BaseModel, computed_field, model_validator, Field

from chatsky.core.context import Context

from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from chatsky.core.service.types import (
    ServiceRuntimeInfo,
    ExtraHandlerType,
    ExtraHandlerFunction,
    ExtraHandlerRuntimeInfo,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from chatsky.core.pipeline import Pipeline


class ComponentExtraHandler(BaseModel, extra="forbid", arbitrary_types_allowed=True):
    """
    Class, representing an extra handler for pipeline components.

    A component extra handler is a set of functions, attached to pipeline component (before or after it).
    Extra handlers should execute supportive tasks (like time or resources measurement, minor data transformations).
    Extra handlers should NOT edit context or pipeline, use services for that purpose instead.
    """

    functions: List[ExtraHandlerFunction] = Field(default_factory=list)
    """
    A list or instance of :py:data:`~.ExtraHandlerFunction`.
    """
    stage: ClassVar[ExtraHandlerType] = ExtraHandlerType.UNDEFINED
    """
    An :py:class:`~.ExtraHandlerType`, specifying whether this handler will
    be executed before or after pipeline component.
    """
    timeout: Optional[float] = None
    """
    (for asynchronous only!) Maximum component execution time (in seconds),
    if it exceeds this time, it is interrupted.
    """
    requested_async_flag: Optional[bool] = None
    """
    Requested asynchronous property.
    """

    @model_validator(mode="before")
    @classmethod
    def functions_validator(cls, data: Any):
        """
        Add support for initializing from a `Callable` or List[`Callable`].
        Casts `functions` to `list` if it's not already.
        """
        if isinstance(data, list):
            result = {"functions": data}
        elif callable(data):
            result = {"functions": [data]}
        else:
            result = data

        if isinstance(result, dict):
            if ("functions" in result) and (not isinstance(result["functions"], list)):
                result["functions"] = [result["functions"]]
        return result

    @computed_field(repr=False)
    def calculated_async_flag(self) -> bool:
        return all([asyncio.iscoroutinefunction(func) for func in self.functions])

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
        Method for executing one of the extra handler functions (before or after).
        If the function is not set, nothing happens.

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
        Property for retrieving info dictionary about this extra handler.

        :return: Info dict, containing its fields as well as its type.
            All not set fields there are replaced with `None`.
        """
        return {
            "type": type(self).__name__,
            "timeout": self.timeout,
            "asynchronous": self.asynchronous,
            "functions": [func.__name__ for func in self.functions],
        }


class BeforeHandler(ComponentExtraHandler):
    """
    A handler for extra functions that are executed before the component's main function.

    :param functions: A list of callables that will be executed
        before the component's main function.
    :type functions: List[ExtraHandlerFunction]
    :param timeout: Optional timeout for the execution of the extra functions, in
        seconds.
    :param requested_async_flag: Optional flag that indicates whether the extra functions
        should be executed asynchronously. The default value of the flag is True
        if all the functions in this handler are asynchronous.
    """

    stage: ClassVar[ExtraHandlerType] = ExtraHandlerType.BEFORE


class AfterHandler(ComponentExtraHandler):
    """
    A handler for extra functions that are executed after the component's main function.

    :param functions: A list of callables that will be executed
        after the component's main function.
    :type functions: List[ExtraHandlerFunction]
    :param timeout: Optional timeout for the execution of the extra functions, in
        seconds.
    :param requested_async_flag: Optional flag that indicates whether the extra functions
        should be executed asynchronously. The default value of the flag is True
        if all the functions in this handler are asynchronous.
    """

    stage: ClassVar[ExtraHandlerType] = ExtraHandlerType.AFTER


ComponentExtraHandlerInitTypes: TypeAlias = Union[
    ComponentExtraHandler,
    Annotated[dict, "dict following the ComponentExtraHandler data model"],
    Annotated[Callable, "a singular function for the extra handler"],
    Annotated[List[Callable], "functions for the extra handler"],
]
"""Types that :py:class:`~.ComponentExtraHandler` can be validated from."""
