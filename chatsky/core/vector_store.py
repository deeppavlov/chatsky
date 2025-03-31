from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging
from uuid import uuid4
from context import Context
from message import Message
from service import Service
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

logger = logging.getLogger(__name__)


class VectorStoreConfig(BaseModel):
    """Configuration model for vector store initialization."""

    collection_name: str = "default"
    """Name of the collection in vector database. Defaults to "default"."""
    top_k: int = 3
    """Number of top results to return during retrieval. Defaults to 3."""
    persist_directory: Optional[str] = None
    """Directory path for persistent storage. Defaults to None."""
    model_name: str = "DeepPavlov/rubert-base-cased"
    """Name of the embedding model. Defaults to "DeepPavlov/rubert-base-cased"."""


class VectorStoreService:
    """
    Abstract base class for vector store services.

    Provides common interface for document storage and retrieval operations.
    Must be subclassed with specific vector database implementations.
    """

    def __init__(self, config: VectorStoreConfig):
        """
        Initialize the vector store service with configuration.

        :param config: Configuration parameters for the vector store.
        """
        self.config = config
        self.initialized = False

    async def initialize(self, ctx: Context):
        """
        Initialize connection to the vector database and register with context.

        :param ctx: Framework context object where the vector store will be registered.

        :raises RuntimeError: If initialization fails.
        """
        if not self.initialized:
            ctx.framework_data.vector_store = self
            self.initialized = True
            logger.info("Vector store initialized")

    async def add_documents(self, documents: List[Message], metadata: dict[Optional]):
        """
        Add documents to the vector store.

        :param documents: List of Message objects to be stored.
        :param metadata: Optional metadata to associate with documents.

        :raises NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError

    async def retrieve(self, query: str) -> List[Message]:
        """
        Retrieve documents similar to the query.

        :param query: Search query string.

        :return: List of matching Message objects.

        :raises NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError


class ChromaVectorStore(VectorStoreService):
    """
    Chroma DB implementation of VectorStoreService.

    Provides concrete implementation using Chroma vector database.
    """

    def __init__(self, config: VectorStoreConfig):
        """
        Initialize Chroma client with given configuration.

        :param config: Configuration parameters.

        :raises Exception: If initialization fails.
        """
        super().__init__(config)
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name=config.model_name)
            self.client = Chroma(
                collection_name=config.collection_name,
                embedding_function=self.embeddings,
                persist_directory=config.persist_directory,
            )
            logger.info(
                "Chroma client initialized for collection: %s", config.collection_name
            )
        except Exception as e:
            logger.error("Failed to initialize Chroma: %s", str(e))
            raise

    async def add_documents(
        self, documents: List[Message], metadata: dict[Optional] = None
    ):
        """
        Add documents to Chroma collection with optional metadata.

        :param documents: List of Message objects to store.
        :param metadata: Metadata dictionary to associate with documents.

        :raises Exception: If document addition fails.
        """
        try:
            docs = [
                Document(page_content=msg.text, metadata=metadata) for msg in documents
            ]
            uuids = [str(uuid4()) for _ in range(len(documents))]
            self.client.add_documents(docs, ids=uuids)
            logger.info("Added %d documents to Chroma", len(documents))
        except Exception as e:
            logger.error("Error adding documents: %s", str(e))
            raise

    async def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """
        Retrieve similar documents from Chroma.

        :param query: Search query string.

        :return: List of dictionaries containing:
                - text: Document content
                - metadata: Associated metadata

        :raises Exception: If retrieval operation fails.
        """
        try:
            results = self.client.similarity_search(query=query, k=self.config.top_k)
            return [
                {"text": doc.page_content, "metadata": doc.metadata} for doc in results
            ]
        except Exception as e:
            logger.error("Error retrieving documents: %s", str(e))
            raise


class RetrieverService(Service):
    """
    Service for retrieving relevant documents based on user queries.

    Integrates with the vector store to perform similarity searches.
    """

    async def __call__(self, ctx: Context):
        """
        Execute document retrieval using the current message in context.

        :param ctx: Framework context containing:
                - requests: Message history
                - framework_data: Storage for vector store and results

        :raises ValueError: If vector store is not initialized.
        """
        if not hasattr(ctx.framework_data, "vector_store"):
            raise ValueError("VectorStore not initialized")

        last_message = ctx.requests[ctx.current_turn_id]
        if not last_message.text:
            logger.warning("Empty query in retriever")
            ctx.framework_data.retrieved_docs = []
            return

        try:
            results = await ctx.framework_data.vector_store.retrieve(last_message.text)
            ctx.framework_data.retrieved_docs = results
            logger.debug("Retrieved %s documents", len(results))
        except Exception as e:
            logger.error("Retrieval failed: %s", str(e))
            ctx.framework_data.retrieved_docs = []
