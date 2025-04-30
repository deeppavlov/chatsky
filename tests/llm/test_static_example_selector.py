import asyncio

from pydantic import BaseModel, Field

from chatsky.llm.example_selector import Example, StaticExampleSelector


class ResponseModel(BaseModel):
    sum: float = Field(description="Sum of the numbers")
    prod: float = Field(description="Product of the numbers")


class RequestModel(BaseModel):
    operand_1: float = Field(description="The first operand")
    operand_2: float = Field(description="The second operand")


class TestStaticExampleSelector:

    selector = StaticExampleSelector([])

    def test_add_example(self):

        ground_truth = [Example(input='{"operand_1":0.0,"operand_2":8.0}', output=ResponseModel(sum=8.0, prod=0.0))]

        self.selector.add_example(
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": ResponseModel(sum=8.0, prod=0.0)}
        )

        assert self.selector.root == ground_truth

    def test_select_examples(self):

        ground_truth = [
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": '{"sum":8.0,"prod":0.0}'},
        ]

        result = self.selector.select_examples(input_variables={})
        assert result == ground_truth

    async def test_aadd_example(self):

        ground_truth = [
            Example(input='{"operand_1":0.0,"operand_2":8.0}', output=ResponseModel(sum=8.0, prod=0.0)),
            Example(input=RequestModel(operand_1=-1.0, operand_2=-2.0), output=ResponseModel(sum=-3.0, prod=2.0)),
        ]

        await self.selector.aadd_example(
            {"input": RequestModel(operand_1=-1.0, operand_2=-2.0), "output": ResponseModel(sum=-3.0, prod=2.0)}
        )

        assert self.selector.root == ground_truth

    async def test_aselect_examples(self):

        ground_truth = [
            {"input": '{"operand_1":0.0,"operand_2":8.0}', "output": '{"sum":8.0,"prod":0.0}'},
            {"input": '{"operand_1":-1.0,"operand_2":-2.0}', "output": '{"sum":-3.0,"prod":2.0}'},
        ]
        result = await self.selector.aselect_examples(input_variables={})

        assert result == ground_truth
