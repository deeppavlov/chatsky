import asyncio
from typing import Any, Dict, List

import pytest
import numpy as np
from langchain_core.example_selectors.base import BaseExampleSelector
from langchain_core.example_selectors import LengthBasedExampleSelector
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field, RootModel

from chatsky import MISC, RESPONSE
from chatsky.llm.example_selector import Example, StaticExampleSelector, to_langchain_context
from chatsky.responses.llm import LLMResponse


class ExamplePrompt(BaseModel, arbitrary_types_allowed=True):
    examples: StaticExampleSelector | BaseExampleSelector


class ResponseModel(BaseModel):
    sum: float = Field(description="Sum of the numbers")
    prod: float = Field(description="Product of the numbers")


class RequestModel(BaseModel):
    operand_1: float = Field(description="The first operand")
    operand_2: float = Field(description="The second operand")


class MockCustomExampleSelector(BaseExampleSelector, RootModel):

    root: List[Example]

    def add_example(self, example: Dict[str, str]) -> Any:
        self.root.append(Example.model_validate(example))

    def unpack_model(self, example_part: str | BaseModel) -> str:
        return str(example_part.model_dump_json()) if isinstance(example_part, BaseModel) else example_part

    def select_examples(self, input_variables: Dict[str, str]) -> List[dict]:
        subset = np.random.choice(self.root, input_variables["size"], input_variables["replace"])
        return [
            {"input": self.unpack_model(example.input), "output": self.unpack_model(example.output)}
            for example in subset
        ]


### Tests


@pytest.fixture(scope="function")
def static_selector_fixture():
    def static_selector(examples: List[Example]):
        return StaticExampleSelector(examples)

    return static_selector


@pytest.fixture(scope="function")
def node_fixture():
    def setted_node(use_static_selector: bool):

        np.random.seed(0)
        node = {RESPONSE: LLMResponse(llm_model_name="my_model", prompt="Add numbers and return an answer.")}
        test_examples = [
            {"input": '{"operand_1":3.0,"operand_2":4.0}', "output": '{"sum":7.0,"prod":12.0}'},
            {"input": RequestModel(operand_1=5.0, operand_2=6.0), "output": '{"sum":11.0,"prod":30.0}'},
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": ResponseModel(sum=8.0, prod=0.0)},
            {"input": RequestModel(operand_1=-1.0, operand_2=-2.0), "output": ResponseModel(sum=-3.0, prod=2.0)},
        ]

        if use_static_selector == True:
            node[MISC] = ExamplePrompt(examples=test_examples)
        else:
            node[MISC] = ExamplePrompt(examples=MockCustomExampleSelector(test_examples))
        return node

    return setted_node


class TestIntegrationStaticExampleSelector:
    def test_select_examples(self, node_fixture):

        node = node_fixture(use_static_selector=True)

        ground_truth = [
            {"input": '{"operand_1":3.0,"operand_2":4.0}', "output": '{"sum":7.0,"prod":12.0}'},
            {"input": '{"operand_1":5.0,"operand_2":6.0}', "output": '{"sum":11.0,"prod":30.0}'},
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": '{"sum":8.0,"prod":0.0}'},
            {"input": '{"operand_1":-1.0,"operand_2":-2.0}', "output": '{"sum":-3.0,"prod":2.0}'},
        ]
        assert node["MISC"].examples.select_examples(input_variables={}) == ground_truth


class TestIntegrationCustomExampleSelector:

    def test_select_examples(self, node_fixture):

        node = node_fixture(use_static_selector=False)

        ground_truth = [
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": '{"sum":8.0,"prod":0.0}'},
            {"input": '{"operand_1":-1.0,"operand_2":-2.0}', "output": '{"sum":-3.0,"prod":2.0}'},
            {"input": '{"operand_1":5.0,"operand_2":6.0}', "output": '{"sum":11.0,"prod":30.0}'},
        ]

        assert ground_truth == node["MISC"].examples.select_examples(input_variables={"size": 3, "replace": False})


class TestStaticExampleSelector:

    def test_add_example(self, static_selector_fixture):

        selector = static_selector_fixture([])

        ground_truth = [Example(input='{"operand_1":0.0,"operand_2":8.0}', output=ResponseModel(sum=8.0, prod=0.0))]

        selector.add_example({"input": '{"operand_1":0.0,"operand_2":8.0}', "output": ResponseModel(sum=8.0, prod=0.0)})

        assert selector.root == ground_truth

    def test_select_examples(self, static_selector_fixture):

        selector = static_selector_fixture(
            [{"input": '{"operand_1":0.0,"operand_2":8.0}', "output": ResponseModel(sum=8.0, prod=0.0)}]
        )

        ground_truth = [
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": '{"sum":8.0,"prod":0.0}'},
        ]

        result = selector.select_examples(input_variables={})
        assert result == ground_truth

    async def test_aadd_example(self, static_selector_fixture):

        selector = static_selector_fixture(
            [{"input": '{"operand_1":0.0,"operand_2":8.0}', "output": ResponseModel(sum=8.0, prod=0.0)}]
        )

        ground_truth = [
            Example(input='{"operand_1":0.0,"operand_2":8.0}', output=ResponseModel(sum=8.0, prod=0.0)),
            Example(input=RequestModel(operand_1=-1.0, operand_2=-2.0), output=ResponseModel(sum=-3.0, prod=2.0)),
        ]

        await selector.aadd_example(
            {"input": RequestModel(operand_1=-1.0, operand_2=-2.0), "output": ResponseModel(sum=-3.0, prod=2.0)}
        )

        assert selector.root == ground_truth

    async def test_aselect_examples(self, static_selector_fixture):

        selector = static_selector_fixture(
            [
                {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": ResponseModel(sum=8.0, prod=0.0)},
                {"input": RequestModel(operand_1=-1.0, operand_2=-2.0), "output": ResponseModel(sum=-3.0, prod=2.0)},
            ]
        )

        ground_truth = [
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": '{"sum":8.0,"prod":0.0}'},
            {"input": '{"operand_1":-1.0,"operand_2":-2.0}', "output": '{"sum":-3.0,"prod":2.0}'},
        ]
        result = await selector.aselect_examples(input_variables={})

        assert result == ground_truth


class TestToLangchainContext:

    async def test_empty_selector(self, static_selector_fixture):

        selector = static_selector_fixture([])

        messages = await to_langchain_context(example_selector=selector, input_variables={})
        assert messages == []

    async def test_selector_with_content(self, static_selector_fixture):

        selector = static_selector_fixture([{"input": "7, 6", "output": "13"}, {"input": "8, -9", "output": "-1"}])

        ground_truth = [
            HumanMessage(content="7, 6", additional_kwargs={}, response_metadata={}),
            AIMessage(content="13", additional_kwargs={}, response_metadata={}),
            HumanMessage(content="8, -9", additional_kwargs={}, response_metadata={}),
            AIMessage(content="-1", additional_kwargs={}, response_metadata={}),
        ]

        messages = await to_langchain_context(example_selector=selector, input_variables={})
        assert messages == ground_truth

    async def test_langchain_selector(self):

        example_prompt = PromptTemplate(input_variables=["input", "output"], template="Input: {input}\nOutput: {output}")

        selector = LengthBasedExampleSelector(
            examples =  [
                {"input": '{"operand_1":3.0,"operand_2":4.0}', "output": '{"sum":7.0,"prod":12.0}'},
                {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": '{"sum":8.0,"prod":0.0}'},
                {"input": '{"operand_1":5.0,"operand_2":6.0}', "output": '{"sum":11.0,"prod":30.0}'},
            ],
            example_prompt = example_prompt,
            max_length= 11
        )

        ground_truth = [
            HumanMessage(content='{"operand_1":3.0,"operand_2":4.0}', additional_kwargs={}, response_metadata={}),
            AIMessage(content='{"sum":7.0,"prod":12.0}', additional_kwargs={}, response_metadata={}),
            HumanMessage(content='{"operand_1":0.0,"operand_2":8.0}', additional_kwargs={}, response_metadata={}),
            AIMessage(content='{"sum":8.0,"prod":0.0}', additional_kwargs={}, response_metadata={}),
        ]

        assert await to_langchain_context(selector, input_variables={"key_1": "value_1", "key_2" : "value_2", "key_3": "value_3"}) == ground_truth
