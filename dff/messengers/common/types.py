"""
Types
-----
The Types module contains special types that are used throughout the `DFF Messengers`.
"""

from typing import Callable
from typing_extensions import TypeAlias


PollingInterfaceLoopFunction: TypeAlias = Callable[[], bool]
"""
A function type used in :py:class:`~.PollingMessengerInterface` to control polling loop.
Returns boolean (whether polling should be continued).
"""
