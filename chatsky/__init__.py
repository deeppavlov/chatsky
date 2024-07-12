# -*- coding: utf-8 -*-
# flake8: noqa: F401
from importlib.metadata import version


__version__ = version(__name__)


from chatsky.pipeline import Pipeline
from chatsky.script import Context, Script

import chatsky.__rebuild_pydantic_models__
