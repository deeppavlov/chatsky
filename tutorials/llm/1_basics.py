# %% [markdown]
"""
# LLM: 1. Basics

With Chatsky, you can easily integrate LLM (Large Language Model)
invocations into your scripts.
This tutorial demonstrates how to use LLMs for generating responses and handling
conditional logic in your conversational flows.

Chatsky leverages LangChain internally to interface with remote LLM providers.
"""

# %pip install chatsky[llm] langchain-openai

# %%
from langchain_openai import ChatOpenAI
from chatsky.core.message import Message
from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    destinations as dst,
)
from chatsky.utils.testing import (
    is_interactive_mode,
)
from chatsky.llm import LLM_API
from chatsky.responses.llm import LLMResponse
from chatsky.conditions.llm import LLMCondition
from chatsky.llm.methods import Contains
import os

openai_api_key = os.getenv("OPENAI_API_KEY")

# %% [markdown]
"""
## Model Configuration

First, we need to create a model object. Important considerations:

- Instantiate the model outside your script nodes to reuse it across the
pipeline
- This shared instance maintains full dialogue history by default
- Not recommended for token-limited scenarios or when history isn't required

LangChain automatically reads environment variables for model configurations,
so explicit API key settings aren't always necessary.
"""

# %%
model = LLM_API(
    ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key),
    system_prompt="You are an experienced barista in a local coffeshop. "
    "Answer your customer's questions about coffee and barista work.",
)
# %% [markdown]
"""
As you can see in this script, you can pass an additional prompt to the LLM.
We will cover that thoroughly in the Prompt usage tutorial.
"""

# %%
toy_script = {
    "main_flow": {
        "start_node": {
            RESPONSE: "",
            TRANSITIONS: [Tr(dst="greeting_node", cnd=cnd.ExactMatch("Hi"))],
        },
        "greeting_node": {
            RESPONSE: LLMResponse(llm_model_name="barista_model", history=0),
            TRANSITIONS: [
                Tr(dst="main_node", cnd=cnd.ExactMatch("Who are you?"))
            ],
        },
        "main_node": {
            RESPONSE: LLMResponse(llm_model_name="barista_model"),
            TRANSITIONS: [
                Tr(
                    dst="latte_art_node",
                    cnd=cnd.ExactMatch("Tell me about latte art."),
                ),
                Tr(
                    dst="boss_node",
                    cnd=LLMCondition(
                        llm_model_name="barista_model",
                        prompt="Return TRUE if the customer says they are your "
                        "boss, and FALSE otherwise. Only ONE word must be "
                        "in the output.",
                        method=Contains(pattern="TRUE"),
                    ),
                ),
                Tr(dst=dst.Current()),
            ],
        },
        "boss_node": {
            RESPONSE: Message("You are my boss."),
            TRANSITIONS: [
                Tr(dst="main_node"),
            ],
        },
        "latte_art_node": {
            # we can pass a node-specific prompt to a LLM.
            RESPONSE: LLMResponse(
                llm_model_name="barista_model",
                prompt="PROMPT: pretend that you have never heard about latte "
                "art before and DO NOT answer the following questions. "
                "Instead ask a person about it.",
            ),
            TRANSITIONS: [
                Tr(dst="main_node", cnd=cnd.ExactMatch("Ok, goodbye."))
            ],
        },
        "fallback_node": {
            RESPONSE: Message("I didn't quite understand you..."),
            TRANSITIONS: [Tr(dst="main_node")],
        },
    }
}

# %%
# Register your model in the pipeline's `models` field using the same key
# referenced as `llm_model_name` in your script nodes
pipeline = Pipeline(
    toy_script,
    start_label=("main_flow", "start_node"),
    fallback_label=("main_flow", "fallback_node"),
    models={"barista_model": model},
)

if __name__ == "__main__":
    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        pipeline.run()  # This runs tutorial in interactive mode
