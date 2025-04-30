"""
Example selection.
----------
This module provides support for example guided generation.
"""

import asyncio
from typing import Any, Dict, List

from langchain_core.example_selectors.base import BaseExampleSelector
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field, RootModel


class Example(BaseModel):
    """Class that holds an example"""

    input: str | BaseModel
    """input may be in form of a string or a custom pydantic model derived from the BaseModel"""
    output: str | BaseModel
    """output may be in form of a string or a custom pydantic model derived from the BaseModel"""


async def to_langchain_context(example_selector: BaseExampleSelector, input_variables: Dict[str, str]) -> None:

    result = []
    for example in await example_selector.aselect_examples(input_variables):

        result.append(HumanMessage(content=example["input"]))
        result.append(AIMessage(content=example["output"]))

    return result


class StaticExampleSelector(BaseExampleSelector, RootModel):

    root: List[Example]

    def add_example(self, example: Dict[str, str]) -> Any:
        self.root.append(Example.model_validate(example))

    def unpack_model(self, example_part: str | BaseModel) -> str:
        return str(example_part.model_dump_json()) if isinstance(example_part, BaseModel) else example_part

    def select_examples(self, input_variables: Dict[str, str]) -> List[dict]:
        return [
            {"input": self.unpack_model(example.input), "output": self.unpack_model(example.output)}
            for example in self.root
        ]
