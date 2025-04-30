import asyncio

from langchain_core.messages import AIMessage, HumanMessage

from chatsky.llm.example_selector import StaticExampleSelector, to_langchain_context


class TestToLangchainContext:

    example_selector = StaticExampleSelector([])

    async def test_empty_selector(self):
        messages = await to_langchain_context(example_selector=self.example_selector, input_variables={})
        assert messages == []

    async def test_selector_with_content(self):

        self.example_selector.add_example({"input": "7, 6", "output": "13"})
        self.example_selector.add_example({"input": "8, -9", "output": "-1"})

        ground_truth = [
            HumanMessage(content="7, 6", additional_kwargs={}, response_metadata={}),
            AIMessage(content="13", additional_kwargs={}, response_metadata={}),
            HumanMessage(content="8, -9", additional_kwargs={}, response_metadata={}),
            AIMessage(content="-1", additional_kwargs={}, response_metadata={}),
        ]

        messages = await to_langchain_context(example_selector=self.example_selector, input_variables={})
        assert messages == ground_truth
