import asyncio
import logging
import inspect
from typing import Optional, List

from df_engine.core import Context, Actor

from .utils import collect_defined_constructor_parameters_to_dict, _get_attrs_with_updates, wrap_sync_function_in_async
from ..types import ServiceRuntimeInfo, WrapperStage, WrapperBuilder, WrapperFunction

logger = logging.getLogger(__name__)


class Wrapper:
    """TODO: update docs
    Class, representing a wrapper.
    A wrapper is a set of two functions, one run before and one after pipeline component.
    Wrappers should execute supportive tasks (like time or resources measurement, minor data transformations).
    Wrappers should NOT edit context or actor, use services for that purpose instead.
    It accepts constructor parameters:
        `before` - function to be executed before component
        `after` - function to be executed after component
        `name` - wrapper name
    """

    def __init__(
        self,
        functions: WrapperBuilder,
        timeout: Optional[int] = None,
        asynchronous: Optional[bool] = None,
    ):
        overridden_parameters = collect_defined_constructor_parameters_to_dict(
            timeout=timeout, asynchronous=asynchronous
        )
        if isinstance(functions, Wrapper):
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
            self.calculated_async_flag = all([asyncio.iscoroutinefunction(function) for function in self.functions])
            self.stage: WrapperStage = WrapperStage.UNDEFINED
        else:
            raise Exception(f"Unknown type for ServiceGroup {functions}")

    @property
    def asynchronous(self) -> bool:
        """
        Property, that indicates, whether this component is synchronous or asynchronous.
        It is calculated according to following rule:
            1. If component can be asynchronous and `requested_async_flag` is set, it returns `requested_async_flag`
            2. If component can be asynchronous and `requested_async_flag` isn't set, it returns True
            3. If component can't be asynchronous and `requested_async_flag` is False or not set, it returns False
            4. If component can't be asynchronous and `requested_async_flag` is True,
                an Exception is thrown in constructor
        Returns bool.
        """
        return self.calculated_async_flag if self.requested_async_flag is None else self.requested_async_flag

    async def _run_function(
        self, function: WrapperFunction, ctx: Context, actor: Actor, component_info: ServiceRuntimeInfo
    ):
        handler_params = len(inspect.signature(function).parameters)
        if handler_params == 1:
            await wrap_sync_function_in_async(function, ctx)
        elif handler_params == 2:
            await wrap_sync_function_in_async(function, ctx, actor)
        elif handler_params == 3:
            await wrap_sync_function_in_async(
                function,
                ctx,
                actor,
                {
                    "function": function,
                    "stage": self.stage,
                    "component": component_info,
                },
            )
        else:
            raise Exception(
                f"Too many parameters required for component {component_info['name']} {self.stage.name}"
                f" wrapper handler '{function.__name__}': {handler_params}!"
            )

    async def _run(self, ctx: Context, actor: Actor, component_info: ServiceRuntimeInfo):
        """
        Method for executing one of the wrapper functions (before or after).
        If the function is not set, nothing happens.
        :stage: - current WrapperStage (before or after).
        :ctx: - current dialog context.
        :actor: - actor, associated with current pipeline.
        :component_info: - associated component's info dictionary.
        Returns None.
        """

        """
        Method for retrieving runtime info about this wrapper.
        It embeds runtime info of the component it wraps under `component` key.
        :stage: - current WrapperStage (before or after).
        :component_info: - associated component's info dictionary.
        Returns a WrapperRuntimeInfo dict where all not set fields are replaced with '[None]'.
        """
        if self.asynchronous:
            futures = [self._run_function(function, ctx, actor, component_info) for function in self.functions]
            for function, future in zip(self.functions, asyncio.as_completed(futures)):
                try:
                    await future
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Component {component_info['name']} {self.stage.name} wrapper '{function.__name__}' timed out!"
                    )

        else:
            for function in self.functions:
                await self._run_function(function, ctx, actor, component_info)

    async def __call__(self, ctx: Context, actor: Actor, component_info: ServiceRuntimeInfo):
        """
        A method for calling pipeline components.
        It sets up timeout if this component is asynchronous and executes it using `_run` method.
        :ctx: (required) - current dialog Context.
        :actor: - this Pipeline Actor or None if this is a service, that wraps Actor.
        Returns Context if this is a synchronous service or Awaitable if this is an asynchronous component or None.
        """
        if self.asynchronous:
            task = asyncio.create_task(self._run(ctx, actor, component_info))
            return await asyncio.wait_for(task, timeout=self.timeout)
        else:
            return await self._run(ctx, actor, component_info)

    @property
    def info_dict(self) -> dict:
        """
        Property for retrieving info dictionary about this wrapper.
        Returns info dict, containing its fields as well as its type.
        All not set fields there are replaced with '[None]'.
        """
        return {
            "type": type(self).__name__,
            "timeout": self.timeout,
            "asynchronous": self.asynchronous,
            "functions": [function.__name__ for function in self.functions],
        }
