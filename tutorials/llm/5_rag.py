# %% [markdown]
"""
# LLM: 5. RAG integration

Chatsky supports vector storages from Langchain.
This tutorial demonstrates how to get documents from vectore storage to use in pipeline.
"""
# %%
import os
from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
)

from chatsky.llm.rag import get_documents
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

# %% [markdown]
"""
## Storage initialize

The first step is to initialize the vector storage with a set of texts.
For more information, see the [Langchain documentation](https://python.langchain.com/docs/concepts/vectorstores/).
"""
# %%
texts = [
    "In a hole in the ground there lived a hobbit.",
    "Not a nasty, dirty, wet hole, filled with the ends of worms and an oozy smell, nor yet a dry, bare, sandy hole with nothing in it to sit down on or to eat.",
    "It was a hobbit-hole, and that means comfort.",
    "It had a perfectly round door like a porthole, painted green, with a shiny yellow brass knob in the exact middle.",
    "The hobbit was a very well-to-do hobbit, and his name was Baggins.",
    "The Bagginses had lived in the neighborhood of The Hill for time out of mind.",
]

docs = [Document(page_content=chunk) for chunk in texts]
openai_api_key = os.getenv("OPENAI_API_KEY")
embeddings = OpenAIEmbeddings(api_key=openai_api_key)

vec_store = InMemoryVectorStore.from_documents(docs, embeddings)

# %% [markdown]
"""
## Pipeline initialize 

Next step is to initialize the Chatsky [pipeline](https://github.com/deeppavlov/chatsky/blob/master/docs/source/user_guides/basic_conceptions.rst). 
This will require a dialog script and a dictionary with previously initialized vector storages.
"""
# %%
toy_script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: [Tr(dst="node1", cnd=cnd.ExactMatch("Hi"))],
        },
        "node1": {
            RESPONSE: "Hi, how are you?",
            TRANSITIONS: [
                Tr(dst="node2", cnd=cnd.ExactMatch("I'm fine, how are you?"))
            ],
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: [
                Tr(dst="node3", cnd=cnd.ExactMatch("Let's talk about music."))
            ],
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: [Tr(dst="node4", cnd=cnd.ExactMatch("Ok, goodbye."))],
        },
        "node4": {
            RESPONSE: "Bye",
            TRANSITIONS: [Tr(dst="node1", cnd=cnd.ExactMatch("Hi"))],
        },
        "fallback_node": {
            RESPONSE: "Ooops",
            TRANSITIONS: [Tr(dst="node1", cnd=cnd.ExactMatch("Hi"))],
        },
    }
}
doc_retrievers = {"in_memory_store": vec_store}

pipeline = Pipeline(
    toy_script,
    start_label=("main_flow", "start_node"),
    fallback_label=("main_flow", "fallback_node"),
    doc_retrievers=doc_retrievers,
)
# %% [markdown]
"""
Now you can use the document retrieval.
"""
# %%
retrieve_docs = get_documents(
    pipeline=pipeline,
    retriever_name="in_memory_store",
    query="Where did the hobbit live?",
    k=1
)
# retrieve_docs= [(Document(id='doc_id', metadata={}, page_content='In a hole in the ground there lived a hobbit.')]
