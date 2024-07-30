from typing import Union
import logging

from pydantic import BaseModel, Field

from chatsky.core.script_function import BaseCondition, ConstCondition, BaseDestination, ConstDestination, BasePriority, ConstPriority


logger = logging.getLogger(__name__)


class Transition(BaseModel):
    cnd: Union[BaseCondition, ConstCondition] = Field(default=True)
    dst: Union[BaseDestination, ConstDestination]
    priority: Union[BasePriority, ConstPriority] = Field(default=None)
