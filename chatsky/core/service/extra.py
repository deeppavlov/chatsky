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
import abc
from typing import Optional, List, Any, ClassVar, Union, Callable, TYPE_CHECKING
from typing_extensions import Annotated, TypeAlias

from pydantic import BaseModel, model_validator, Field

from chatsky.core.context import Context

from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from chatsky.core.service.types import (
    ExtraHandlerType,
    ExtraHandlerFunction,
    ExtraHandlerRuntimeInfo,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from chatsky.core.service import PipelineComponent


class ComponentExtraHandler(BaseModel, abc.ABC, extra="forbid", arbitrary_types_allowed=True):
    """
    Class, representing an extra handler for pipeline components.

    A component extra handler is a set of functions, attached to pipeline component (before or after it).
    Extra handlers should execute supportive tasks (like time or resources measurement, minor data transformations).
    """

    functions: List[ExtraHandlerFunction] = Field(default_factory=list)
    """
    A list or instance of :py:data:`~.ExtraHandlerFunction`.
    """
    stage: ClassVar[ExtraHandlerType]
    """
    An :py:class:`~.ExtraHandlerType`, specifying whether this handler will
    be executed before or after pipeline component.
    """
    timeout: Optional[float] = None
    """
    Maximum component execution time (in seconds),
    if it exceeds this time, it is interrupted.
    """
    concurrent: bool = False
    """
    A flag that indicates whether the extra handler's functions
    should be executed concurrently. False by default.
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

    async def _run_function(self, func: ExtraHandlerFunction, ctx: Context, component: PipelineComponent):
        handler_params = len(inspect.signature(func).parameters)
        if handler_params == 1:
            await wrap_sync_function_in_async(func, ctx)
        elif handler_params == 2:
            extra_handler_runtime_info = ExtraHandlerRuntimeInfo(stage=self.stage, component=component)
            await wrap_sync_function_in_async(func, ctx, extra_handler_runtime_info)
        else:
            raise Exception(
                f"Too many parameters required for component {component.name} {self.stage}"
                f" wrapper handler '{func.__name__}': {handler_params}!"
            )

    async def _run(self, ctx: Context, component_info: PipelineComponent):
        """
        Method for executing one of the extra handler functions (before or after).
        If the function is not set, nothing happens.

        :param ctx: current dialog context.
        :param component_info: associated component's `self` object.
        :return: `None`
        """

        if self.concurrent:
            await asyncio.gather(*[self._run_function(func, ctx, component_info) for func in self.functions])
        else:
            for func in self.functions:
                await self._run_function(func, ctx, component_info)

    async def __call__(self, ctx: Context, component_info: PipelineComponent):
        """
        A method for calling an extra handler.
        It sets up a timeout and executes it using `_run` method.

        :param ctx: (required) Current dialog `Context`.
        :param component_info: associated component's `self` object.
        """
        task = asyncio.create_task(self._run(ctx, component_info))
        await asyncio.wait_for(task, timeout=self.timeout)


class BeforeHandler(ComponentExtraHandler):
    """
    A handler for extra functions that are executed before the component's main function.

    :param functions: A list of callables that will be executed
        before the component's main function.
    :type functions: List[ExtraHandlerFunction]
    :param timeout: Optional timeout for the execution of the extra functions, in
        seconds.
    :param concurrent: Optional flag that indicates whether the extra functions
        should be executed concurrently. False by default.
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
    :param concurrent: Optional flag that indicates whether the extra functions
        should be executed concurrently. False by default.
    """

    stage: ClassVar[ExtraHandlerType] = ExtraHandlerType.AFTER


ComponentExtraHandlerInitTypes: TypeAlias = Union[
    ComponentExtraHandler,
    Annotated[dict, "dict following the ComponentExtraHandler data model"],
    Annotated[Callable, "a singular function for the extra handler"],
    Annotated[List[Callable], "functions for the extra handler"],
]
"""Types that :py:class:`~.ComponentExtraHandler` can be validated from."""
