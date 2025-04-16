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

        flat_items, items_with_models = self._flatten_llm_group_slot(self)
        captions = {}
        for child_name, slot_item in flat_items.items():
            captions[child_name] = (slot_item.return_type, Field(description=slot_item.caption, default=None))

        logger.debug(f"Flattened group slot: {flat_items}")
        DynamicGroupModel = create_model("DynamicGroupModel", **captions)
        logger.debug(f"DynamicGroupModel: {DynamicGroupModel}")

        history_messages = context_to_history(
            ctx, self.history, filter_func=FromModel(), llm_model_name=self.llm_model_name, max_size=1000
        )
        if history_messages == []:
            history_messages = [message_to_langchain(ctx.last_request, ctx)]

        extracted_items = {}
        for key, item in items_with_models.items():
            if isinstance(item, LLMSlot):
                res = await item.extract_value(ctx)
            elif isinstance(item, LLMGroupSlot):
                res = await item.get_value(ctx)
            else:
                res = SlotNotExtracted
            extracted_items[key] = res

        result: Message = await ctx.pipeline.models.get(self.llm_model_name, None)._ainvoke(
            history=history_messages, message_schema=DynamicGroupModel
        )
        result_json = result.model_dump()
        logger.debug(f"Result JSON: {result_json}")

        # Convert flat dict to nested structure
        nested_result = {}
        for key, value in result_json.items():
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

        # Combine extracted_items with the nested result
        for key, value in extracted_items.items():
            if isinstance(value, ExtractedValueSlot):
                nested_result[key] = value
            elif isinstance(value, ExtractedGroupSlot):
                nested_result[key] = self._dict_to_extracted_slots(value)
            else:
                nested_result[key] = SlotNotExtracted

        return self._dict_to_extracted_slots(nested_result)

    def _dict_to_extracted_slots(self, d):
        """
        Convert nested dictionary of ExtractedValueSlots into an ExtractedGroupSlot.
        """
        if not isinstance(d, dict):
            return d
        return ExtractedGroupSlot(**{k: self._dict_to_extracted_slots(v) for k, v in d.items()})

    def _flatten_llm_group_slot(
        self, slot, parent_key=""
    ) -> Tuple[Dict[str, LLMSlot], list[Union[LLMSlot, LLMGroupSlot]]]:
        """
        Convert potentially nested group slot into a dictionary with
        flat keys.
        Nested keys are flattened as concatenations via ".".

        As such, values in the returned dictionary are only of type :py:class:`LLMSlot`.
        """
        items = {}
        items_with_models = {}
        # filter out items with `llm_model_name` specified
        # to a separate list. Other should go to the flattening list
        for key, value in slot.__pydantic_extra__.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if value.llm_model_name:
                items_with_models[new_key] = value
                continue
            if isinstance(value, LLMGroupSlot):
                items.update(self._flatten_llm_group_slot(value, new_key))
            else:
                items[new_key] = value
        return items, items_with_models
