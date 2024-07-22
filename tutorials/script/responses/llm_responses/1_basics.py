# %% [markdown]
"""
# LLM Responses: 1. Basics

Using Chatsky you can easily add LLM invocations to your script.
In this tutorial we will see how to use LLM responses.
Chatsky uses langchain under the hood to connect to the remote models.
"""

# %pip install chatsky
# %pip install langchain-openai
# or install langchain for the model of your choise

# %%
from chatsky.script import Message
from chatsky.script.conditions import exact_match
from chatsky.script.conditions import std_conditions as cnd
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
Keep in mind, that if you instantiate model object outside of the script,
it will be reused across all the nodes and therefore it will store all dialogue history.
This is not advised if you are short on tokens or if you do not need to store all dialogue history.
Alternatively you can instantiate model object inside of RESPONSE field in the nodes you need.
"""

# %%
model = LLMResponse(ChatOpenAI(model="gpt-3.5-turbo"), system_prompt="You are an experienced barista in a local coffeshop. Answer your customers questions about coffee and barista work.")

# %% [markdown]
"""
Also you can pass images to the LLM, just pass them as attachments to your message.
"""

# %%
toy_script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(""),
            TRANSITIONS: {"greeting_node": exact_match("Hi")},
        },
        "greeting_node": {
            RESPONSE: model.respond(),
            TRANSITIONS: {"main_node": exact_match("i'm fine, how are you?")},
        },
        "main_node": {
            RESPONSE: model.respond(),
            TRANSITIONS: {
                "latte_art_node": exact_match("Tell me about latte art."),
                "image_desc_node": exact_match("Tell me what coffee is it?")},
        },
        "latte_art_node": {
            RESPONSE: model.respond(prompt="PROMPT: pretend that you have never heard about latte art before."),
            TRANSITIONS: {"image_desc_node": exact_match("Ok, goodbye.")},
        },
        "image_desc_node": {
            # we expect user to send some images of coffee.
            RESPONSE: model.respond(prompt="PROMPT: user will give you some images of coffee. Describe them."),
            TRANSITIONS: {"main_node": cnd.true()},
        },
        "fallback_node": {
            RESPONSE: Message("I didn't quite understand you..."),
            TRANSITIONS: {"main_node": cnd.true()},
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
