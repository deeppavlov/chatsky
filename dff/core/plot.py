# %%

import logging
from typing import Callable, Optional, Any

from pydantic import BaseModel, validator, validate_arguments, Extra, root_validator

from .keywords import GLOBAL
from .types import NodeLabelType, ConditionType
from .normalization import normalize_node_label, normalize_response, normalize_processing, normalize_transitions

logger = logging.getLogger(__name__)
# TODO: add tests


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

    @root_validator(pre=True)
    def preproc_global(cls, values):
        if "plot" in values and GLOBAL in values["plot"]:
            values["plot"][GLOBAL] = {GLOBAL: values["plot"][GLOBAL]}
        return values

    @validator("plot")
    def is_not_empty(cls, fields: dict) -> dict:
        if not any(fields.values()):
            raise ValueError("Plot does not have nodes")
        return fields

    @validate_arguments
    def get_node(self, node_label: NodeLabelType, flow_label: str = "") -> Optional[Node]:
        normalized_node_label = normalize_node_label(node_label, flow_label)
        flow_label = normalized_node_label[0]
        node_label = normalized_node_label[1]
        node = self.plot.get(flow_label, {}).get(node_label)
        if node is None:
            logger.warn(f"Unknown pair(flow_label:node_label) = {flow_label}:{node_label}")
        return node

    def __getitem__(self, k):
        return self.plot[k]

    def get(self, k, item=None):
        return self.plot.get(k, item)

    def keys(self):
        return self.plot.keys()

    def items(self):
        return self.plot.items()

    def values(self):
        return self.plot.values()

    def __iter__(self):
        return self.plot
