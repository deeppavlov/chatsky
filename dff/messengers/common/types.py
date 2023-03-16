"""
Types
-----
The Types module contains two special types that are used throughout the `DFF Messengers`.
The first type is used for the messenger interface to client interaction and the second one
to control the polling loop.
"""
from typing import Callable, Any, Hashable, Awaitable
from typing_extensions import TypeAlias

from dff.script import Context


PipelineRunnerFunction: TypeAlias = Callable[[Any, Hashable], Awaitable[Context]]
"""
A function type for messenger_interface-to-client interaction.
Accepts anything (user input) and hashable value (current context id), returns string (answer from pipeline).
"""


PollingInterfaceLoopFunction: TypeAlias = Callable[[], bool]
"""
A function type used in :py:class:`~.PollingMessengerInterface` to control polling loop.
Returns boolean (whether polling should be continued).
"""
