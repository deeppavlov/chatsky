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
    '''How to answer a user.'''

    input : str | BaseModel = Field(description="An example of the user's query.")

    output: str | BaseModel = Field(description="A desired answer example")


class StaticExampleSelector(BaseExampleSelector, RootModel):
		
        root: List[Example]

        def add_example(self, example: Example) -> Any:
            self.root.append(Example(input=example["input"], output=example["output"]))

        def select_examples(self) -> List[Dict]:
            sample = []
            for example in self.root:
                tmp = {}
                tmp["input"] = example.input
                tmp["output"] = str(example.output.model_dump_json()) if isinstance(example.output, BaseModel) else example.output
                sample.append(tmp)
            return sample

        def to_langchain_context(self) -> None:

            result = []
            for example in self.root:
                result.append(HumanMessage(content=example.input))
                
                if isinstance(example.output, BaseModel):
                    result.append(AIMessage(content=str(example.output.model_dump_json())))
                    continue
                result.append(AIMessage(content=example.output))

            return result


if __name__ == "__main__":

    ###### TEST IMPORTS ###########
    from pprint import pprint
    from chatsky import RESPONSE, MISC
    from chatsky.responses.llm import LLMResponse

    ###### Placeholder ExamplePrompt Class ###########

    class ExamplePrompt(BaseModel, arbitrary_types_allowed=True):
        examples: StaticExampleSelector | BaseExampleSelector

        async def __call__(self):
            examples: list[dict[str, str]] = await self.examples.select_examples({"input": ctx.last_request.text})
    
    ##### "Simple" examples (Support for structured output) ################

    print("Simple examples      <------------")
    print()
    
    node = {
    RESPONSE: LLMResponse(
        llm_model_name="my_model",
        prompt="Add numbers and return an answer."
    ),
    MISC: ExamplePrompt(examples=[
            {"input": "3, 4", "output": "7"},
            {"input": "5, 6", "output": "11"}
        ])
    }

    pprint(node['MISC'].examples.to_langchain_context()) # check that to_langchain_context() works as intended
    print()

    node['MISC'].examples.add_example({"input": "-1, 2", "output": "1"}) # check that we can add example via add_example method
    pprint(node['MISC'].examples.to_langchain_context())
    print()

    pprint(node['MISC'].examples.select_examples())
    print()


   ##### Custom examples (Support for structured output) ################
    
    class MyResponseModel(BaseModel):
        sum: float = Field(description="Sum of the numbers.")
        prod: float = Field(description="Product of the numbers")
    
    node = {
        RESPONSE: LLMResponse(
            llm_model_name="my_model",
            prompt="Do mathematical operations and return result in json similar to examples.",
            message_schema=MyResponseModel
        ),
        MISC: ExamplePrompt(examples=[
            {"input": "3, 4", "output": MyResponseModel(sum=7, prod=12)}
        ])
    }

    
    print("Custom examples      <------------")
    print()
    
    pprint(node['MISC'].examples.to_langchain_context()) # check that to_langchain_context() works as intended
    print()
    
    node['MISC'].examples.add_example({"input": "-1, 2", "output": MyResponseModel(sum=1, prod=-2)}) # check that we can add example via add_example method
    pprint(node['MISC'].examples.to_langchain_context())
    print()

    pprint(node['MISC'].examples.select_examples())
    print()
    
    
    

    ##### Same "tests", but now we have a custom Selector deived from BaseExampleSelector

    import numpy as np

    class RandomSelector(BaseExampleSelector, BaseModel):
        '''
        Custom Selector class just for testing purposes
        '''
        examples: List[Example]
        k: int = 1
        replace: bool = False

        def add_example(self, example: Example) -> None:
            self.examples.append(Example(input=example["input"], output=example["output"]))
        
        def select_examples(self, k=k, replace=replace) -> List[Dict[str, str]]:
            subset = np.random.choice(self.examples, size=k, replace=replace)
            sample = []
            for example in subset:
                tmp = {}
                tmp["input"] = example.input
                tmp["output"] = str(example.output.model_dump_json()) if isinstance(example.output, BaseModel) else example.output
                sample.append(tmp)
            return sample

        def to_langchain_context(self) -> None:

            result = []
            for example in self.select_examples():
                result.append(HumanMessage(content=example["input"]))
                
                if isinstance(example["output"], BaseModel):
                    result.append(AIMessage(content=str(example.output.model_dump(mode="json"))))
                    continue
                result.append(AIMessage(content=example["output"]))

            return result

     ##### "Simple" examples (Support for structured output) ################

    print("Simple examples * Custom Selector      <------------")
    print()
    
    node = {
    RESPONSE: LLMResponse(
        llm_model_name="my_model",
        prompt="Add numbers and return an answer."
    ),
    MISC: ExamplePrompt(examples=RandomSelector(examples=[
            {"input": "3, 4", "output": "7"},
            {"input": "5, 6", "output": "11"}
        ]))
    }
    
    print(node['MISC'].examples)

    pprint(node['MISC'].examples.to_langchain_context()) # check that to_langchain_context() works as intended
    print()

    node['MISC'].examples.add_example({"input": "-1, 2", "output": "1"}) # check that we can add example via add_example method
    pprint(node['MISC'].examples.to_langchain_context())
    print()

    pprint(node['MISC'].examples.select_examples())
    print()

    print("Custom examples * Custom Selector      <------------")
    print()

    node = {
        RESPONSE: LLMResponse(
            llm_model_name="my_model",
            prompt="Do mathematical operations and return result in json similar to examples.",
            message_schema=MyResponseModel
        ),
        MISC: ExamplePrompt(examples=RandomSelector(examples=[
            {"input": "3, 4", "output": MyResponseModel(sum=7, prod=12)}
        ]))
    }
    
    pprint(node['MISC'].examples.to_langchain_context()) # check that to_langchain_context() works as intended
    print()
    
    node['MISC'].examples.add_example({"input": "-1, 2", "output": MyResponseModel(sum=1, prod=-2)}) # check that we can add example via add_example method
    pprint(node['MISC'].examples.to_langchain_context())
    print()

    pprint(node['MISC'].examples.select_examples())
    print()

    # StaticExampleSelector(root=[{"input": "3, 4", "output": "7"}]
    #print(node['MISC'].examples)