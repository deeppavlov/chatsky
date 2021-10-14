# %%

import logging
from typing import Callable, Optional, Any

from pydantic import BaseModel, validator, Extra

from .types import NodeLabelType, ConditionType
from .normalization import normalize_response, normalize_processing, normalize_transitions, normalize_plot

logger = logging.getLogger(__name__)


class Node(BaseModel, extra=Extra.forbid):
    transitions: dict[NodeLabelType, ConditionType] = {}
    response: Optional[Any] = None
    processing: dict[Any, Callable] = {}
    misc: dict = {}

    _normalize_transitions = validator("transitions", allow_reuse=True)(normalize_transitions)
    _normalize_response = validator("response", allow_reuse=True)(normalize_response)
    _normalize_processing = validator("processing", allow_reuse=True)(normalize_processing)


class Plot(BaseModel, extra=Extra.forbid):
    plot: dict[str, dict[str, Node]]

    _normalize_plot = validator("plot", allow_reuse=True, pre=True)(normalize_plot)

    def __getitem__(self, key):
        return self.plot[key]

    def get(self, key, item=None):
        return self.plot.get(key, item)

    def keys(self):
        return self.plot.keys()

    def items(self):
        return self.plot.items()

    def values(self):
        return self.plot.values()

    def __iter__(self):
        return self.plot
