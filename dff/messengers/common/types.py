from typing import Callable, Any, Hashable, Awaitable

from dff.script import Context

"""
A function type for messenger_interface-to-client interaction.
Accepts anything (user input) and hashable vaklue (current dialog id), returns string (answer from pipeline).
"""
PipelineRunnerFunction = Callable[[Any, Hashable], Awaitable[Context]]


"""
A function type used in PollingMessengerInterface to control polling loop.
Returns boolean (whether polling should be continued).
"""
PollingInterfaceLoopFunction = Callable[[], bool]
