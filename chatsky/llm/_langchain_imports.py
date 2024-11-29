from typing import Any

try:
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages.base import BaseMessage
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from langchain_core.outputs.llm_result import LLMResult

    langchain_available = True
except ImportError:  # pragma: no cover
    StrOutputParser = Any
    BaseChatModel = Any
    BaseMessage = Any
    HumanMessage = Any
    SystemMessage = Any
    AIMessage = Any
    LLMResult = Any

    langchain_available = False


def check_langchain_available():  # pragma: no cover
    if not langchain_available:
        raise ImportError("Langchain is not available. Please install it with `pip install chatsky[llm]`.")
