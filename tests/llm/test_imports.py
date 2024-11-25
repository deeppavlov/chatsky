import langchain_core.messages
import pytest
from typing import Any

try:
    import langchain_core
except ImportError:
    pytest.skip(...)


def test_imports(monkeypatch):
    monkeypatch.delattr(langchain_core.messages, "HumanMessage")

    from chatsky.llm._langchain_imports import langchain_available, HumanMessage, check_langchain_available

    assert langchain_available is False
    assert HumanMessage == Any
    with pytest.raises(ImportError):
        check_langchain_available()
