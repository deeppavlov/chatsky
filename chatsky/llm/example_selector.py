"""
Example selection.
----------
This module provides support for example guided generation.
"""

from typing import List, Dict, Any

from pydantic import BaseModel, Field, RootModel

from langchain_core.example_selectors.base import BaseExampleSelector
from langchain_core.messages import HumanMessage, AIMessage


class Example(BaseModel):
    '''Class that holds an example'''

    input : str | BaseModel
    '''input may be in form of a string or a custom pydantic model derived from the BaseModel'''
    output: str | BaseModel
    '''output may be in form of a string or a custom pydantic model derived from the BaseModel'''


def to_langchain_context(example_selector: BaseExampleSelector) -> None:

    result = []
    for example in example_selector.select_examples():
        
        result.append(HumanMessage(content=example["input"]))
        result.append(AIMessage(content=example["output"]))

    return result


class StaticExampleSelector(BaseExampleSelector, RootModel):
		
        root: List[Example]

        def add_example(self, example: Example) -> Any:
            self.root.append(Example.model_validate(example))
        
        def unpack_model(self, example_part: str | BaseModel) -> str:
            return str(example_part.model_dump_json()) if isinstance(example_part, BaseModel) else example_part
        
        def select_examples(self) -> List[Dict[str, str]]:
            return [{"input": self.unpack_model(example.input), "output": self.unpack_model(example.output)} for example in self.root]
