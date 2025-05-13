from typing import Dict, Any
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from chatsky.responses.base_response import BaseResponse


class RAGPromptBuilder(BaseResponse):
    def __init__(self, vector_store_url: str, retriever_model: str, **kwargs):
        super().__init__(**kwargs)
        self.vector_store = QdrantClient(url=vector_store_url)
        self.retriever = SentenceTransformer(retriever_model)

    def execute(self, user_query: str, ctx: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        if "cached_rag_context" in ctx:
            context = ctx["cached_rag_context"]
        else:
            query_embedding = self.retriever.encode(user_query)
            results = self.vector_store.search(collection_name="docs", query_vector=query_embedding, limit=3)
            context = "\n".join([hit.payload["text"] for hit in results])
            ctx["cached_rag_context"] = context

        prompt = f"Контекст: {context}\nВопрос: {user_query}"
        return {"prompt": prompt}


"""
rag_node:
  RESPONSE:
    LLMResponse:
      prompt: "{{ RAGPromptBuilder(user_query=user_query, ctx=ctx)['prompt'] }}"
  MISC:
    rag_prompt_builder:
      class: "chatsky.responses.RAGPromptBuilder"
      params:
        vector_store_url: "http://localhost:6333"
        retriever_model: "all-MiniLM-L6-v2"

next_node:
  RESPONSE:
    CustomPythonResponse:
      module: "some_module.NextHandler"
      params:
        reused_data: "{{ ctx.cached_rag_context }}"



node1:
  RESPONSE:
    CustomPythonResponse:
      set_ctx:  # Примерная запись (уточните синтаксис Chatsky)
        key: "rag_data"
        value: "{{ some_data }}"

node2:
  RESPONSE:
    LLMResponse:
      prompt: "Используем данные из node1: {{ ctx.rag_data }}"
"""
