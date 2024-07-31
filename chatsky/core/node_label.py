from __future__ import annotations

from typing import Optional, TypeAlias, Union, Tuple, TYPE_CHECKING, Annotated

from pydantic import BaseModel, model_validator, ValidationInfo, ValidationError


def _get_current_flow_name(ctx) -> Optional[str]:
    current_node = ctx._get_current_node()
    return current_node.flow.name


class NodeLabel(BaseModel):
    flow_name: Optional[str] = None
    node_name: str

    @model_validator(mode="before")
    @classmethod
    def validate_from_str_or_tuple(cls, data, info: ValidationInfo):
        if isinstance(data, str):
            flow_name = None
            context = info.context
            if isinstance(context, dict):
                flow_name = _get_current_flow_name(context.get("ctx"))
            return {"flow_name": flow_name, "node_name": data}
        elif isinstance(data, tuple):
            if len(data) == 2 and isinstance(data[0], str) and isinstance(data[1], str):
                return {"flow_name": data[0], "node_name": data[1]}
            else:
                raise ValidationError(f"Cannot validate NodeLabel from {data!r}: tuple should contain 2 strings.")
        return data


NodeLabelInitTypes: TypeAlias = Union[
    NodeLabel,
    Annotated[str, "node_name, flow name equal to current flow's name"],
    Tuple[Annotated[str, "flow_name"], Annotated[str, "node_name"]],
    Annotated[dict, "dict repr of NodeLabel"]
]
"""Types that :py:class:`~.NodeLabelInitTypes` can be validated from."""


class AbsoluteNodeLabel(NodeLabel):
    flow_name: str

    @model_validator(mode="before")
    @classmethod
    def validate_from_node_label(cls, data, info: ValidationInfo):
        if isinstance(data, NodeLabel):
            flow_name = data.flow_name
            if flow_name is None:
                context = info.context
                if isinstance(context, dict):
                    flow_name = _get_current_flow_name(context.get("ctx"))
            return {"flow_name": flow_name, "node_name": data.node_name}
        return data



AbsoluteNodeLabelInitTypes: TypeAlias = Union[
    AbsoluteNodeLabel,
    Tuple[Annotated[str, "flow_name"], Annotated[str, "node_name"]],
    Annotated[dict, "dict repr of AbsoluteNodeLabel"]
]
"""Types that :py:class:`~.AbsoluteNodeLabelInitTypes` can be validated from."""
