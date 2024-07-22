# %% [markdown]
"""
# LLM Responses: 1. Basics

Using Chatky you can easily add LLM invocations to your script.
In this tutorial we will see how to use LLM responses.
Chatsky uses langchain under the hood to connect to the remote models.
"""

# %pip install chatsky
# %pip install langchain-openai
# or install langchain for the model of your choise

# %%
from chatsky.script import Message
from chatsky.script.conditions import exact_match
from chatsky.script import RESPONSE, TRANSITIONS
from chatsky.pipeline import Pipeline
from chatsky.utils.testing import (
    is_interactive_mode,
    run_interactive_mode,
)
from chatsky.script.responses.llm.llm_response import LLMResponse

import getpass
import os
os.environ["OPENAI_API_KEY"] = getpass.getpass()

from langchain_openai import ChatOpenAI

# %% [markdown]
"""
Now we need to create a model object.
"""

# %%
model = LLMResponse(ChatOpenAI(model="gpt-3.5-turbo"), system_prompt="You are an experienced barista in a local coffeshop. Answer your customers questions about coffee and barista work.")

# %%
toy_script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(""),
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
        "node1": {
            RESPONSE: model.respond,
            TRANSITIONS: {"node2": exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: model.respond,
            TRANSITIONS: {"node3": exact_match("Tell me about latte art.")},
        },
        "node3": {
            RESPONSE: model.respond,
            TRANSITIONS: {"node4": exact_match("Ok, goodbye.")},
        },
        "node4": {
            RESPONSE: model.respond,
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
        "fallback_node": {
            RESPONSE: Message("I didn't quite understand you..."),
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
    }
}

# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

if __name__ == "__main__":
    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
