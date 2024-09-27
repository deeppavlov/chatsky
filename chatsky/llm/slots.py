"""
LLM Slots.
---------
This module contains Slots based on LLMs structured outputs, that can easily infer requested information from an unstructured user's request.
"""

from chatsky.slots.slots import ValueSlot, SlotNotExtracted
from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Union, Optional, Dict
from chatsky.core import Context, Message

class LLMSlot(ValueSlot):
    """
    LLMSlot is a slot type that extract information described in `caption` parameter using LLM.
    """
    caption: str
    model: BaseChatModel

    async def extract_value(self, ctx: Context) -> Union[str, SlotNotExtracted]:
        request_text = ctx.last_request.text
        
        # Dynamically create a Pydantic model based on the caption
        class DynamicModel(BaseModel):
            value: str = Field(description=self.caption)

        try:
            structured_model = self.model.with_structured_output(DynamicModel)
        except Exception as e:
            return SlotNotExtracted(f"This type of model cannot be used for structured output: {e}")
        
        try:
            result = await structured_model.ainvoke(request_text)
            return result.value
        except Exception as e:
            return SlotNotExtracted(f"Failed to extract value: {str(e)}")
