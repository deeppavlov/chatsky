"""
Types
-----
This module defines type aliases used throughout the ``Core.Service`` module.

The classes and special types in this module can include data models,
data structures, and other types that are defined for type hinting.
"""

from __future__ import annotations
from enum import unique, Enum
from typing import Callable, Union, Awaitable, Optional, Any, Protocol, Hashable, TYPE_CHECKING
from typing_extensions import TypeAlias
from pydantic import BaseModel


if TYPE_CHECKING:
    from chatsky.core import Context, Message
    from chatsky.core.service import PipelineComponent


class PipelineRunnerFunction(Protocol):
    """
    Protocol for pipeline running.
    """

    def __call__(
        self, message: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
    ) -> Awaitable[Context]:
        """
        :param message: User request for pipeline to process.
        :param ctx_id:
            ID of the context that the new request belongs to.
            Optional, None by default.
            If set to `None`, a new context will be created with `message` being the first request.
        :param update_ctx_misc:
            Dictionary to be passed as an argument to `ctx.misc.update`.
            This argument can be used to store values in the `misc` dictionary before anything else runs.
            Optional; None by default.
            If set to `None`, `ctx.misc.update` will not be called.
        :return:
            Context instance that pipeline processed.
            The context instance has the id of `ctx_id`.
            If `ctx_id` is `None`, context instance has an id generated with `uuid.uuid4`.
        """


@unique
class ComponentExecutionState(str, Enum):
    """
    Enum, representing pipeline component execution state.
    These states are stored in :py:attr:`~chatsky.core.context.FrameworkData.service_states`,
    that should always be requested with ``NOT_RUN`` being default fallback.
    Following states are supported:

    - NOT_RUN: component has not been executed yet (the default one),
    - RUNNING: component is currently being executed,
    - FINISHED: component executed successfully,
    - FAILED: component execution failed.
    """

    NOT_RUN = "NOT_RUN"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


@unique
class ExtraHandlerType(str, Enum):
    """
    Enum, representing extra handler execution stage: before or after the wrapped function.
    The following types are supported:

    - BEFORE: extra handler function called before component,
    - AFTER: extra handler function called after component.
    """

    BEFORE = "BEFORE"
    AFTER = "AFTER"


ExtraHandlerConditionFunction: TypeAlias = Callable[[str], bool]
"""
A function type used when adding an extra handler to a service group to determine
whether extra handler should be added to components of the service group.

Accepts a single argument - path of a subcomponent in a group.
Return bool - whether to add extra handler to the subcomponent.
"""


ExtraHandlerFunction: TypeAlias = Union[
    Callable[["Context"], Any],
    Callable[["Context", "ExtraHandlerRuntimeInfo"], Any],
]
"""
A function type for creating extra handler (before and after functions).
Can accept current dialog context and current extra handler info.
"""


class ExtraHandlerRuntimeInfo(BaseModel):
    """
    Information passed to :py:data:`.ExtraHandlerFunction`.
    """

    stage: ExtraHandlerType
    """
    :py:class:`.ExtraHandlerType` -- either "BEFORE" or "AFTER".
    """
    component: PipelineComponent
    """
    Component object that called the extra handler.
    """
