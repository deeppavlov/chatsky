from typing import List, Optional
from langchain_core.vectorstores import VectorStore
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from chatsky import Pipeline


async def get_documents(
    pipeline: Pipeline,
    retriever_name: str,
    query: str,
    threshold: Optional[float] = None,
    k: int = 4,
) -> List[Document]:
    if not pipeline.doc_retrievers[retriever_name]:
        raise NameError("doc_retriever with the specified name does not exist")

    doc_retriever = pipeline.doc_retrievers[retriever_name]

    if isinstance(doc_retriever, VectorStore):
        results = await doc_retriever.asimilarity_search_with_score(query, k=k)
        if threshold:
            results = [(doc, score) for doc, score in results if score >= threshold]

    elif isinstance(doc_retriever, BaseRetriever):
        if threshold:
            raise NotImplementedError(
                "Threshold filtering is not implemented for BaseRetriever."
            )
        doc_retriever.k = k
        results = doc_retriever.invoke(query)

    else:
        raise TypeError("Unsupported retriever type")

    return results
