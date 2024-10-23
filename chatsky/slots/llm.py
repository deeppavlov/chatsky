"""
LLM Slots.
---------
This module contains Slots based on LLMs structured outputs, that can easily infer requested information from an unstructured user's request.
"""

from chatsky.slots.slots import ValueSlot, SlotNotExtracted, GroupSlot, ExtractedGroupSlot, ExtractedValueSlot
from pydantic import BaseModel, Field, create_model
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Union, Optional, Dict, Any
from chatsky.core import Context, Message
from collections.abc import MutableMapping
import asyncio
import logging
logger = logging.getLogger(__name__)

class LLMSlot(ValueSlot, frozen=True):
    """
    LLMSlot is a slot type that extract information described in `caption` parameter using LLM.
    """
    caption: str
    model: Optional[Any] = None

    def __init__(self, caption, model=None):
        super().__init__(
            caption = caption,
            model=model
        )

    async def extract_value(self, ctx: Context) -> Union[str, SlotNotExtracted]:
        request_text = ctx.last_request.text
        if request_text == '':
            return SlotNotExtracted
        # Dynamically create a Pydantic model based on the caption
        class DynamicModel(BaseModel):
            value: str = Field(description=self.caption)
        
        # model = create_model("DynamicModel",)

        structured_model = self.model.with_structured_output(DynamicModel)
    
        result = await structured_model.ainvoke(request_text)
        return result.value


class LLMGroupSlot(GroupSlot):
    
    __pydantic_extra__: Dict[str, Union[LLMSlot, "LLMGroupSlot"]]
    model: Any

    @property
    def caption(self):
        cap = {}
        for child_name, child in self.__pydantic_extra__.items():
            logger.debug(f"Child.caption is {child.caption}, and it is {type(child.caption)}")
            cap[child_name] = (type(child.caption), Field(description=child.caption, default=None))
        
        return cap

    async def get_value(self, ctx: Context) -> ExtractedGroupSlot:
        flat_items = self.__flatten_llm_group_slot(self)
        captions = {}
        for child_name, caption in flat_items.items():
            captions[child_name] = (type(caption), Field(description=caption, default=None))
        
        logger.debug(f"Flattened group slot: {flat_items}")
        DynamicGroupModel = create_model("DynamicGroupModel", **captions)
        logger.debug(f"DynamicGroupModel: {DynamicGroupModel}")
        
        structured_model = self.model.with_structured_output(DynamicGroupModel)
        result = await structured_model.ainvoke(ctx.last_request.text)
        result_json = result.model_dump()
        logger.debug(f"Result JSON: {result_json}") 

        if self.allow_partially_extracted:
            res = {name: ExtractedValueSlot.model_construct(is_slot_extracted=True, extracted_value=result_json[name]) for name in result_json if result_json[name] is not None}
        else:
            res = {name: ExtractedValueSlot.model_construct(is_slot_extracted=True, extracted_value=result_json[name]) for name in result_json}
        return ExtractedGroupSlot(**res)


    def __flatten_llm_group_slot(self, slot, parent_key=''):
        items = {}
        for key, value in slot.__pydantic_extra__.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, LLMGroupSlot):
                items.update(self.__flatten_llm_group_slot(value, new_key))
            else:
                items[new_key] = value.caption
        return items
