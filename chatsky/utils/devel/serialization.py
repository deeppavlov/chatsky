from typing import Dict, List, TypeAlias, Union

from pydantic import BaseModel


PydanticValue: TypeAlias = Union[
    List["PydanticValue"],
    Dict[str, "PydanticValue"],
    BaseModel,
    str,
    bool,
    int,
    float,
    None,
]
