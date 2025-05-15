import re
import pytest
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_core.retrievers import BaseRetriever
from unittest.mock import AsyncMock, Mock

from chatsky import Pipeline
from chatsky.llm.rag import get_documents
from chatsky.utils.testing import TOY_SCRIPT


async def mock_asimilarity_search_with_relevance_scores(query, k=4, **kwargs):
    score_threshold = kwargs.pop("score_threshold", None)
    high_score_test_doc = Document(
        id="1", metadata={}, page_content="High score test doc"
    )
    low_score_test_doc = Document(
        id="2", metadata={}, page_content="Low score test doc"
    )
    results = [
        (high_score_test_doc, 0.9),
        (low_score_test_doc, 0.2),
    ]
    if score_threshold is not None:
        results = [(doc, score) for doc, score in results if score >= score_threshold]
    return results


@pytest.fixture
def pipeline_with_retrievers():
    high_score_test_doc = Document(
        id="1", metadata={}, page_content="High score test doc"
    )
    low_score_test_doc = Document(
        id="2", metadata={}, page_content="Low score test doc"
    )
    vec_store = Mock(spec=VectorStore)
    vec_store.asimilarity_search_with_score = AsyncMock(
        return_value=[(high_score_test_doc, 0.9), (low_score_test_doc, 0.2)]
    )
    vec_store.asimilarity_search_with_relevance_scores = AsyncMock(
        side_effect=mock_asimilarity_search_with_relevance_scores
    )

    just_retriever = Mock(spec=BaseRetriever)
    just_retriever.invoke = Mock(return_value=[high_score_test_doc, low_score_test_doc])

    pipeline = Pipeline(script=TOY_SCRIPT, start_label=("greeting_flow", "start_node"))
    pipeline.doc_retrievers = {
        "in_memory_store": vec_store,
        "bm25_retriever": just_retriever,
        "wrong_type_retriever": object(),
    }
    return pipeline


@pytest.mark.parametrize(
    "threshold, expected_docs",
    [
        (None, ["High score test doc", "Low score test doc"]),
        (0.3, ["High score test doc"]),
        (0.95, []),
    ],
)
async def test_get_documents_store(pipeline_with_retrievers, threshold, expected_docs):
    result = await get_documents(
        pipeline_with_retrievers,
        retriever_name="in_memory_store",
        query="What is in the doc?",
        threshold=threshold,
    )

    docs = [doc[0].page_content for doc in result]
    assert docs == expected_docs


async def test_get_documents_retriever(pipeline_with_retrievers):
    result = await get_documents(
        pipeline_with_retrievers,
        retriever_name="bm25_retriever",
        query="What is in the doc?",
    )
    docs = [doc.page_content for doc in result]
    expected_docs = ["High score test doc", "Low score test doc"]
    assert docs == expected_docs


async def test_retriever_with_threshold(pipeline_with_retrievers):
    with pytest.raises(
        TypeError,
        match="Threshold filtering is not implemented for BaseRetriever.",
    ):
        await get_documents(
            pipeline_with_retrievers,
            retriever_name="bm25_retriever",
            query="What is in the doc?",
            threshold=0.3,
        )


async def test_raise_nameerror(pipeline_with_retrievers):
    with pytest.raises(
        ValueError, match="doc_retriever with the specified name does not exist"
    ):
        await get_documents(
            pipeline_with_retrievers,
            retriever_name="some_other_retriever",
            query="What is in the doc?",
        )


async def test_raise_typeerror(pipeline_with_retrievers):
    with pytest.raises(TypeError, match="Unsupported retriever type"):
        await get_documents(
            pipeline_with_retrievers,
            retriever_name="wrong_type_retriever",
            query="What is in the doc?",
        )


async def test_raise_missing_doc_retrievers():
    pipeline = Pipeline(script=TOY_SCRIPT, start_label=("greeting_flow", "start_node"))

    with pytest.raises(
        ValueError,
        match=re.escape(
            "pipeline() missing 1 required positional argument: doc_retrievers"
        ),
    ):
        await get_documents(
            pipeline,
            retriever_name="bm25_retriever",
            query="What is in the doc?",
        )
