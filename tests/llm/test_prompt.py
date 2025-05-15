import pytest
from chatsky.llm.prompt import FewShotExamplePrompt
from chatsky.core import Message, Context
from chatsky.llm._langchain_imports import HumanMessage, AIMessage, SystemMessage

@pytest.mark.asyncio
class TestFewShotExamplePrompt:

    @pytest.fixture
    async def dummy_ctx_hello(self):
        """Контекст с запросом 'hello' """
        ctx = Context()
        ctx.requests[1] = Message(text="hello")
        ctx.current_turn_id = 1
        return ctx

    @pytest.fixture
    async def dummy_ctx_translate(self):
        """Контекст с запросом 'translate: hello'"""
        ctx = Context()
        ctx.requests[1] = Message(text="translate: hello")
        ctx.current_turn_id = 1
        return ctx

    async def test_examples_mode_with_template(self, dummy_ctx_hello):
        """Проверка режима examples + template"""

        prompt = FewShotExamplePrompt(
            template="Q: {input}\nA: {output}",
            examples=[
                {"input": "hello", "output": "hola"},
                {"input": "goodbye", "output": "adiós"},
            ],
            prefix="You are Spanish translator.",
            suffix="Q: {input}\nA:"
        )

        messages = await prompt.to_langchain_messages(dummy_ctx_hello)

        assert len(messages) == 1
        assert isinstance(messages[0], SystemMessage)
        content = messages[0].content[0]["text"]
        assert "You are a Spanish translator." in content
        assert "hello" in content

    async def test_manual_examples_mode(self, dummy_ctx_hello):
        """Проверка режима без template -> manual human+ai messages"""

        prompt = FewShotExamplePrompt(
            examples=[
                {"input": "apple", "output": "manzana"},
                {"input": "banana", "output": "plátano"},
            ]
        )

        messages = await prompt.to_langchain_messages(dummy_ctx_hello)

        assert len(messages) == 4  # 2 Human + 2 AI
        for i in range(0, len(messages), 2):
            assert isinstance(messages[i], HumanMessage)
            assert isinstance(messages[i+1], AIMessage)

        assert messages[0].content == "apple"
        assert messages[1].content == "manzana"
        assert messages[2].content == "banana"
        assert messages[3].content == "plátano"

    async def test_template_with_user_input(self, dummy_ctx_translate):
        """Проверка вставки текущего user input в шаблон"""

        prompt = FewShotExamplePrompt(
            template="Input: {input}\nOutput: {output}",
            examples=[
                {"input": "hello", "output": "hola"},
                {"input": "goodbye", "output": "adiós"},
            ],
            prefix="You are Spanish translator.",
            suffix="Input: {input}\nOutput:"
        )

        messages = await prompt.to_langchain_messages(dummy_ctx_translate)

        assert len(messages) == 1
        assert isinstance(messages[0], SystemMessage)
        content = messages[0].content[0]["text"]
        assert "You are a Spanish translator." in content
        assert "translate: hello" in content