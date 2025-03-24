"""
LLM Slots
---------
Warning! This is an experimental feature.

This module contains Slots based on LLMs structured outputs,
that can easily extract requested information from an unstructured user's request.
"""

from __future__ import annotations

from typing import Union, Dict, TYPE_CHECKING
import logging

from pydantic import BaseModel, Field, create_model

from chatsky.slots.slots import ValueSlot, SlotNotExtracted, GroupSlot, ExtractedGroupSlot, ExtractedValueSlot

if TYPE_CHECKING:
    from chatsky.core import Context


logger = logging.getLogger(__name__)


class LLMSlot(ValueSlot, frozen=True):
    """
    LLMSlot is a slot type that extracts information described in
    `caption` parameter using LLM.
    """

    # TODO:
    # add history (and overall update the class)

    caption: str
    return_type: type = str
    llm_model_name: str = ""

    def __init__(self, caption, llm_model_name=""):
        super().__init__(caption=caption, llm_model_name=llm_model_name)

    async def extract_value(self, ctx: Context) -> Union[str, SlotNotExtracted]:
        request_text = ctx.last_request.text
        if request_text == "":
            return SlotNotExtracted()
        model_instance = ctx.pipeline.models[self.llm_model_name].model

        # Dynamically create a Pydantic model based on the caption
        class DynamicModel(BaseModel):
            value: self.return_type = Field(description=self.caption)

        structured_model = model_instance.with_structured_output(DynamicModel)

        result = await structured_model.ainvoke(request_text)
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
        flat_items = self._flatten_llm_group_slot(self)
        captions = {}
        for child_name, slot_item in flat_items.items():
            captions[child_name] = (slot_item.return_type, Field(description=slot_item.caption, default=None))

        logger.debug(f"Flattened group slot: {flat_items}")
        DynamicGroupModel = create_model("DynamicGroupModel", **captions)
        logger.debug(f"DynamicGroupModel: {DynamicGroupModel}")

        model_instance = ctx.pipeline.models[self.llm_model_name].model
        structured_model = model_instance.with_structured_output(DynamicGroupModel)
        result = await structured_model.ainvoke(request_text)
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

        return self._dict_to_extracted_slots(nested_result)

    def _dict_to_extracted_slots(self, d):
        """
        Convert nested dictionary of ExtractedValueSlots into an ExtractedGroupSlot.
        """
        if not isinstance(d, dict):
            return d
        return ExtractedGroupSlot(**{k: self._dict_to_extracted_slots(v) for k, v in d.items()})

    def _flatten_llm_group_slot(self, slot, parent_key="") -> Dict[str, LLMSlot]:
        """
        Convert potentially nested group slot into a dictionary with
        flat keys.
        Nested keys are flattened as concatenations via ".".

        As such, values in the returned dictionary are only of type :py:class:`LLMSlot`.
        """
        items = {}
        for key, value in slot.__pydantic_extra__.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, LLMGroupSlot):
                items.update(self._flatten_llm_group_slot(value, new_key))
            else:
                items[new_key] = value
        return items
