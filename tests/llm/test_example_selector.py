import asyncio
from typing import Any, Dict, List

import numpy as np
from langchain_core.example_selectors.base import BaseExampleSelector
from pydantic import BaseModel, Field, RootModel

from chatsky import MISC, RESPONSE
from chatsky.llm.example_selector import Example, StaticExampleSelector
from chatsky.responses.llm import LLMResponse


class ExamplePrompt(BaseModel, arbitrary_types_allowed=True):
    examples: StaticExampleSelector | BaseExampleSelector

    async def __call__(self):
        examples: list[dict[str, str]] = await self.examples.select_examples({"input": ctx.last_request.text})


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


class TestStaticExampleSelector:
    node = {
        RESPONSE: LLMResponse(llm_model_name="my_model", prompt="Add numbers and return an answer."),
        MISC: ExamplePrompt(
            examples=[
                {"input": '{"operand_1":3.0,"operand_2":4.0}', "output": '{"sum":7.0,"prod":12.0}'},
                {"input": RequestModel(operand_1=5.0, operand_2=6.0), "output": '{"sum":11.0,"prod":30.0}'},
                {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": ResponseModel(sum=8.0, prod=0.0)},
                {"input": RequestModel(operand_1=-1.0, operand_2=-2.0), "output": ResponseModel(sum=-3.0, prod=2.0)},
            ]
        ),
    }

    def test_select_examples(self):

        ground_truth = [
            {"input": '{"operand_1":3.0,"operand_2":4.0}', "output": '{"sum":7.0,"prod":12.0}'},
            {"input": '{"operand_1":5.0,"operand_2":6.0}', "output": '{"sum":11.0,"prod":30.0}'},
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": '{"sum":8.0,"prod":0.0}'},
            {"input": '{"operand_1":-1.0,"operand_2":-2.0}', "output": '{"sum":-3.0,"prod":2.0}'},
        ]
        assert self.node["MISC"].examples.select_examples(input_variables={}) == ground_truth


class TestCustomExampleSelector:

    node = {
        RESPONSE: LLMResponse(llm_model_name="my_model", prompt="Add numbers and return an answer."),
        MISC: ExamplePrompt(
            examples=MockCustomExampleSelector(
                [
                    {"input": '{"operand_1":3.0,"operand_2":4.0}', "output": '{"sum":7.0,"prod":12.0}'},
                    {"input": RequestModel(operand_1=5.0, operand_2=6.0), "output": '{"sum":11.0,"prod":30.0}'},
                    {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": ResponseModel(sum=8.0, prod=0.0)},
                    {
                        "input": RequestModel(operand_1=-1.0, operand_2=-2.0),
                        "output": ResponseModel(sum=-3.0, prod=2.0),
                    },
                ]
            )
        ),
    }

    def test_select_examples(self):
        ground_truth = [
            {"input": '{"operand_1":3.0,"operand_2":4.0}', "output": '{"sum":7.0,"prod":12.0}'},
            {"input": '{"operand_1":5.0,"operand_2":6.0}', "output": '{"sum":11.0,"prod":30.0}'},
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": '{"sum":8.0,"prod":0.0}'},
            {"input": '{"operand_1":-1.0,"operand_2":-2.0}', "output": '{"sum":-3.0,"prod":2.0}'},
        ]
        cnt = 0
        input_variables = {"size": 3, "replace": False}
        for example in self.node["MISC"].examples.select_examples(input_variables=input_variables):
            for true_example in ground_truth:
                if example == true_example:
                    cnt += 1
                    break

        assert cnt == input_variables["size"]
