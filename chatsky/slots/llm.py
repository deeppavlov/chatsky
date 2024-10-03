"""
LLM Slots.
---------
This module contains Slots based on LLMs structured outputs, that can easily infer requested information from an unstructured user's request.
"""

from chatsky.slots.slots import ValueSlot, SlotNotExtracted, GroupSlot, ExtractedGroupSlot
from pydantic import BaseModel, Field, create_model
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Union, Optional, Dict, Any
from chatsky.core import Context, Message

class LLMSlot(ValueSlot, frozen=True):
    """
    LLMSlot is a slot type that extract information described in `caption` parameter using LLM.
    """
    caption: str
    model: Optional[Any] = None

    def __init__(self, caption, model):
        super().__init__(
            caption = caption,
            model=model
        )

    async def extract_value(self, ctx: Context) -> Union[str, SlotNotExtracted]:
        request_text = ctx.last_request.text
        
        # Dynamically create a Pydantic model based on the caption
        class DynamicModel(BaseModel):
            value: str = Field(description=self.caption)

        structured_model = self.model.with_structured_output(DynamicModel)
    
        result = await structured_model.ainvoke(request_text)
        return result.value


class LLMGroupSlot(GroupSlot):
    
    __pydantic_extra__: Dict[str, LLMSlot]
    model: Any

    async def get_value(self, ctx: Context) -> ExtractedGroupSlot:
        child_captions = {child_name: child.caption for child_name, child in self.__pydantic_extra__.values()}
        DynamicGroupModel = create_model("DynamicGroupModel", **child_captions)
        
        structured_model = self.model.with_structured_output(DynamicGroupModel)
        result = await structured_model.ainvoke(ctx.last_request.text)
        result = result.model_dump()
        return ExtractedGroupSlot(**result)