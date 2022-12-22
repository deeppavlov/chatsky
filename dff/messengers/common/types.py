"""
Types
-----
This module contains two special types.
"""
from typing import Callable, Any, Hashable, Awaitable

from dff.script import Context


PipelineRunnerFunction = Callable[[Any, Hashable], Awaitable[Context]]
"""
A function type for messenger_interface-to-client interaction.
Accepts anything (user input) and hashable vaklue (current dialog id), returns string (answer from pipeline).
"""


PollingInterfaceLoopFunction = Callable[[], bool]
"""
A function type used in `PollingMessengerInterface` to control polling loop.
Returns boolean (whether polling should be continued).
"""
