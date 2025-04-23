"""
LLM Slots
---------
Warning! This is an experimental feature.

This module contains Slots based on LLMs structured outputs,
that can easily extract requested information from an unstructured user's request.
"""

from __future__ import annotations

from typing import Union, Dict, TYPE_CHECKING, Tuple
import logging

from pydantic import BaseModel, Field, create_model

from chatsky.llm.langchain_context import context_to_history, message_to_langchain
from chatsky.llm.filters import FromModel
from chatsky.slots.slots import ValueSlot, SlotNotExtracted, GroupSlot, ExtractedGroupSlot, ExtractedValueSlot

if TYPE_CHECKING:
    from chatsky.core import Context
    from chatsky.core.message import Message


logger = logging.getLogger(__name__)


class LLMSlot(ValueSlot, frozen=True):
    """
    LLMSlot is a slot type that extracts information described in
    `caption` parameter using LLM.
    """

    caption: str
    return_type: type = str
    llm_model_name: str = ""
    history: int = 0

    def __init__(self, caption, return_type, llm_model_name="", history=0):
        super().__init__(caption=caption, return_type=return_type, llm_model_name=llm_model_name, history=history)

    async def extract_value(self, ctx: Context) -> Union[str, SlotNotExtracted]:
        request_text = ctx.last_request.text
        if request_text == "":
            return SlotNotExtracted()

        history_messages = context_to_history(
            ctx, self.history, filter_func=FromModel(), llm_model_name=self.llm_model_name, max_size=1000
        )
        if history_messages == []:
            history_messages = [message_to_langchain(ctx.last_request, ctx)]
        # Dynamically create a Pydantic model based on the caption
        return_type = self.return_type

        class DynamicModel(BaseModel):
            value: return_type = Field(description=self.caption)

        result: DynamicModel = await ctx.pipeline.models[self.llm_model_name]._ainvoke(
            history=history_messages, message_schema=DynamicModel
        )

        return result.value


class LLMGroupSlot(GroupSlot):
    """
    LLMSlots based :py:class:`~.GroupSlot` implementation.
    Fetches data for all LLMSlots in a single API request
    contrary to :py:class:`~.GroupSlot`.
    """

    __pydantic_extra__: Dict[str, Union[LLMSlot, "LLMGroupSlot"]]
    llm_model_name: str

    async def get_value(self, ctx: Context) -> ExtractedGroupSlot:
        request_text = ctx.last_request.text
        if request_text == "":
            return ExtractedGroupSlot()

        # Get all slots grouped by their model names
        model_groups = self._group_slots_by_model(self)
        
        # Process each model group separately
        all_results = {}
        for model_name, slots in model_groups.items():
            if not slots:
                continue
                
            # Create dynamic model for this group
            captions = {}
            for child_name, slot_item in slots.items():
                captions[child_name] = (slot_item.return_type, Field(description=slot_item.caption, default=None))

            DynamicGroupModel = create_model("DynamicGroupModel", **captions)
            logger.debug(f"DynamicGroupModel for {model_name}: {DynamicGroupModel}")

            history_messages = context_to_history(
                ctx, self.history, filter_func=FromModel(), llm_model_name=model_name, max_size=1000
            )
            if history_messages == []:
                history_messages = [message_to_langchain(ctx.last_request, ctx)]

            # Get model and process request
            model = ctx.pipeline.models.get(model_name)
            if model is None:
                logger.warning(f"Model {model_name} not found in pipeline.models")
                continue

            result: Message = await model._ainvoke(
                history=history_messages, message_schema=DynamicGroupModel
            )
            result_json = result.model_dump()
            logger.debug(f"Result JSON for {model_name}: {result_json}")
            
            # Add results to all_results
            all_results.update(result_json)

        # Convert flat dict to nested structure
        nested_result = {}
        for key, value in all_results.items():
            if value is None and self.allow_partial_extraction:
                continue

            current = nested_result
            parts = key.split(".")
            *path_parts, final = parts

            # Build nested dict structure
            for part in path_parts:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the final value
            current[final] = ExtractedValueSlot.model_construct(
                is_slot_extracted=value is not None, extracted_value=value
            )

        return self._dict_to_extracted_slots(nested_result)

    def _group_slots_by_model(self, slot, parent_key="") -> Dict[str, Dict[str, LLMSlot]]:
        """
        Group slots by their llm_model_name.
        Returns a dictionary where keys are model names and values are dictionaries
        of slot paths to slot objects.
        """
        model_groups = {}
        
        for key, value in slot.__pydantic_extra__.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, LLMGroupSlot):
                # Recursively process nested group slots
                nested_groups = self._group_slots_by_model(value, new_key)
                for model_name, slots in nested_groups.items():
                    if model_name not in model_groups:
                        model_groups[model_name] = {}
                    model_groups[model_name].update(slots)
            else:
                # Use the slot's model name or fall back to the group's model name
                model_name = value.llm_model_name or self.llm_model_name
                if model_name not in model_groups:
                    model_groups[model_name] = {}
                model_groups[model_name][new_key] = value
                
        return model_groups

    def _dict_to_extracted_slots(self, d):
        """
        Convert nested dictionary of ExtractedValueSlots into an ExtractedGroupSlot.
        """
        if not isinstance(d, dict):
            return d
        return ExtractedGroupSlot(**{k: self._dict_to_extracted_slots(v) for k, v in d.items()})
