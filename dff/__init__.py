# -*- coding: utf-8 -*-
# flake8: noqa: F401
from importlib.metadata import version


__version__ = version(__name__)


import nest_asyncio

nest_asyncio.apply()

from dff.pipeline import Pipeline
from dff.script import Context, Script

Script.model_rebuild()
