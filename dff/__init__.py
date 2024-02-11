# -*- coding: utf-8 -*-
# flake8: noqa: F401
from importlib.metadata import version


__version__ = version(__name__)


import nest_asyncio

nest_asyncio.apply()

from dff.pipeline import Pipeline
from dff.script import Context, Script

from dff.script.core.message import (
    Location,
    Attachment,
    Audio,
    Video,
    Image,
    Document,
    Attachments,
    Link,
    Button,
    Keyboard,
    Message,
    MultiMessage
)
import dff.script.responses as rsp
import dff.script.labels as lbl
import dff.script.conditions as cnd

Script.model_rebuild()
