# %% [markdown]
"""
# LLM: 1. Basics

Using Chatsky you can easily add LLM invocations to your script.
In this tutorial we will see how to use LLM for responses and conditions.
Chatsky uses langchain under the hood to connect to the remote models.
"""

# %pip install chatsky[llm]

# %%
from chatsky.script import Message
from chatsky.script.conditions import exact_match
from chatsky.script.conditions import std_conditions as cnd
from chatsky.script import labels as lbl
from chatsky.script import RESPONSE, TRANSITIONS
from chatsky.pipeline import Pipeline
from chatsky.utils.testing import (
    is_interactive_mode,
    run_interactive_mode,
)
from chatsky.llm.wrapper import LLM_API, llm_response, llm_condition
from chatsky.llm.methods import Contains


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
Via `history` parameter you can set number of dialogue _turns_ that the model will use as the history. Default value is `5`.
"""

# %%
model = LLM_API(ChatOpenAI(model="gpt-3.5-turbo"), system_prompt="You are an experienced barista in a local coffeshop. Answer your customers questions about coffee and barista work.")

# %% [markdown]
"""
Also you can pass images to the LLM, just pass them as attachments to your message.
As you can see in this script, you can pass an additional prompt to the LLM. We will cover that thoroughly in the Prompt usage tutorial.
"""

# %%
toy_script = {
    "main_flow": {
        "start_node": {
            RESPONSE: Message(""),
            TRANSITIONS: {"greeting_node": exact_match("Hi")},
        },
        "greeting_node": {
            RESPONSE: llm_response(model_name="barista_model", history=0),
            TRANSITIONS: {"main_node": exact_match("Who are you?")},
        },
        "main_node": {
            RESPONSE: llm_response(model_name="barista_model"),
            TRANSITIONS: {
                "latte_art_node": exact_match("Tell me about latte art."),
                "image_desc_node": exact_match("Tell me what coffee is it?"),
                "boss_node": llm_condition(model_name="barista_model",
                                           prompt="PROMPT: return only TRUE if your customer says that he is your boss, or FALSE if he don't. Only ONE word must be in the output.",
                                           method=Contains(pattern="TRUE")),
                lbl.repeat(): cnd.true()},
        },
        "boss_node": {
            RESPONSE: Message("Input your ID number."),
            TRANSITIONS: {
                "main_node": cnd.true(),
            },
        },
        "latte_art_node": {
            # we can pass a node-specific prompt to a LLM.
            RESPONSE: llm_response(model_name="barista_model", prompt="PROMPT: pretend that you have never heard about latte art before and DO NOT answer the following questions. Instead ask a person about it."),
            TRANSITIONS: {"main_node": exact_match("Ok, goodbye.")},
        },
        "image_desc_node": {
            # we expect user to send some images of coffee.
            RESPONSE: llm_response(model_name="barista_model", prompt="PROMPT: user will give you some images of coffee. Describe them."),
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
    start_label=("main_flow", "start_node"),
    fallback_label=("main_flow", "fallback_node"),
    models={"barista_model": model}
)

if __name__ == "__main__":
    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
