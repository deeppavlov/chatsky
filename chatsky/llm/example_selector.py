"""
Example selection.
----------
This module provides support for example guided generation.
"""

from typing import List, Dict

from pydantic import BaseModel, Field

from langchain_core.example_selectors.base import BaseExampleSelector
from langchain_core.messages import HumanMessage, AIMessage


class Example(BaseModel):
    '''How to answer a user.'''

    example_input: str = Field(description="An example of the user's query.")

    example_output: str = Field(description="A desired answer example")


class ExampleSelector(BaseModel, arbitrary_types_allowed=True):
    '''Class for example selection'''

    examples: List[Dict[str, str] | Example] 

    example_selector: BaseExampleSelector

    @staticmethod
    def to_langchain_context(examples: List[Dict[str, str] | Example]):
        """
        Convert list of examples to list of lanchain messages.

        :param examples: list of dictionaries in format {"example_input" : "...", "example_output" : "..."} or
        instances of :py:class:`~chatsky.llm.example_selector.Example`

        :return: List of Langchain message objects.
        """

        result = []
        if len(examples) > 0:
            if isinstance(examples[0], Example):
                result = ExampleSelector.example_to_langchain_context(examples)
            else:
                result = ExampleSelector.dict_to_langchain_context(examples)
        
        return result
    
    @staticmethod
    def dict_to_langchain_context(examples : List[Dict[str, str]]):
        """
        Convert list of examples to list of lanchain messages.

        :param examples: list of dictionaries in format {"example_input" : "...", "example_output" : "..."}

        :return: List of Langchain message objects.
        """

        result = []
        for example in examples:
            result.append(HumanMessage(content=example["example_input"]))
            result.append(AIMessage(content=example["example_output"]))
        return result

    @staticmethod
    def example_to_langchain_context(examples: List[Example]):
        """
        Convert list of examples to list of lanchain messages.

        :param examples: list of instances of :py:class:`~chatsky.llm.example_selector.Example`

        :return: List of Langchain message objects.
        """
        
        result = []
        for example in examples:
            result.append(HumanMessage(content=example.example_input))
            result.append(AIMessage(content=example.example_output))
        return result


if __name__ == "__main__":
    
    START = 1
    END = 10
    import numpy as np

    class RandomSelector(BaseExampleSelector):
        '''
        Custom Selector class just for testing purposes
        '''

        def add_example(self, example: dict[str, str]) -> None:
            pass
        
        def select_examples(self, examples, k=3, replace=False) -> list[dict[str, str] | Example]:
            return np.random.choice(examples, size=k, replace=False)
            

    # Dict-like примеры

    dict_like = [{"example_input" : str(i), "example_output" : str(i+1)} for i in range(START, END + 1, 2)]
    dict_example_selector = ExampleSelector(examples=dict_like, example_selector=RandomSelector())
    
    dict_examples = dict_example_selector.example_selector.select_examples(dict_example_selector.examples, 3)
    
    print(ExampleSelector.to_langchain_context(dict_examples))

    # Pydantic-like примеры

    pydantic_like = [Example(example_input=str(i), example_output=str(i+1)) for i in range(START, END + 1, 2)]
    pydantic_example_selector = ExampleSelector(examples=pydantic_like, example_selector=RandomSelector())

    pydantic_examples = pydantic_example_selector.example_selector.select_examples(pydantic_example_selector.examples, 3)
    
    print(ExampleSelector.to_langchain_context(pydantic_examples))
