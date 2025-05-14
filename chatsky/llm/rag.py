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
    """This function searches for relevant documents using a retriever specified in :py:attr:`Pipeline.doc_retrievers`.
    Supports vector-based retrievers (e.g., FAISS, Chroma) and standard retrievers from LangChain.

    :param pipeline: :py:class:`Pipeline` instance containing registered retrievers.
    :type pipeline: Pipeline
    :param retriever_name: The name of the retriever specified in :py:attr:`Pipeline.doc_retrievers`.
    :type retriever_name: str
    :param query: The query string to search for documents in retriever.
    :type query: str
    :param threshold: Optional similarity score threshold (applied only to VectorStore retrievers), defaults to None
    :type threshold: Optional[float], optional
    :param k: The number of top documents to retrieve, defaults to 4
    :type k: int, optional
    
    :raises TypeError: If :py:attr:`Pipeline.doc_retrievers` is empty or retriever type is unsupported.
    :raises NameError: If the specified retriever name does not exist in :py:attr:`Pipeline.doc_retrievers`.
    :raises NotImplementedError: If threshold filtering is requested for non-vector retrievers.
    
    :return: A list of LangChain :py:class:`Document` objects representing the retrieved results.
    :rtype: List[Document]
    """

    if not pipeline.doc_retrievers:
        raise TypeError("pipeline() missing 1 required positional argument: doc_retrievers")

    elif retriever_name not in pipeline.doc_retrievers:
        raise NameError("doc_retriever with the specified name does not exist")

    doc_retriever = pipeline.doc_retrievers[retriever_name]

    if isinstance(doc_retriever, VectorStore):
        results = await doc_retriever.asimilarity_search_with_score(query, k=k)
        if threshold:
            results = [(doc, score) for doc, score in results if score >= threshold]

    elif isinstance(doc_retriever, BaseRetriever):
        if threshold:
            raise NotImplementedError("Threshold filtering is not implemented for BaseRetriever.")
        doc_retriever.k = k
        results = doc_retriever.invoke(query)

    else:
        raise TypeError("Unsupported retriever type")

    return results
