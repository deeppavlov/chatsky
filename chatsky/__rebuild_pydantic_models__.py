# flake8: noqa: F401

from chatsky.core.service.types import ExtraHandlerRuntimeInfo
from chatsky.script import Context, Script

Script.model_rebuild()
Context.model_rebuild()
ExtraHandlerRuntimeInfo.model_rebuild()
