# %% [markdown]
"""
# LLM: 1. Basics

Using Chatsky you can easily add LLM invocations to your script.
In this tutorial we will see how to use LLM for responses and conditions.
Chatsky uses langchain under the hood to connect to the remote models.
"""

# %pip install chatsky[llm]

# %%
from chatsky.core.message import Message
from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    destinations as dst
    # all the aliases used in tutorials are available for direct import
    # e.g. you can do `from chatsky import Tr` instead
)
from chatsky.utils.testing import (
    is_interactive_mode,
    run_interactive_mode,
)
from chatsky.llm import LLM_API, llm_response, llm_condition
from chatsky.llm.methods import Contains

import os

os.environ["OPENAI_API_KEY"] = "<TOKEN>"

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
model = LLM_API(
    ChatOpenAI(model="gpt-3.5-turbo"),
    system_prompt="You are an experienced barista in a local coffeshop. Answer your customers questions about coffee and barista work.",
)

# %% [markdown]
"""
Also you can pass images to the LLM, just pass them as attachments to your message.
As you can see in this script, you can pass an additional prompt to the LLM. We will cover that thoroughly in the Prompt usage tutorial.
"""

# %%
toy_script = {
    "main_flow": {
        "start_node": {
            RESPONSE: "",
            TRANSITIONS: [Tr(dst="greeting_node", cnd=cnd.ExactMatch("Hi"))],
        },
        "greeting_node": {
            RESPONSE: llm_response(model_name="barista_model", history=0),
            TRANSITIONS: [Tr(dst="main_node", cnd=cnd.ExactMatch("Who are you?"))],
        },
        "main_node": {
            RESPONSE: llm_response(model_name="barista_model"),
            TRANSITIONS: [
                Tr(dst="latte_art_node", cnd=cnd.ExactMatch("Tell me about latte art.")),
                Tr(dst="image_desc_node", cnd=cnd.ExactMatch("Tell me what coffee is it?")),
                Tr(dst="boss_node", cnd=llm_condition(
                    model_name="barista_model",
                    prompt="Return only TRUE if your customer says that he is your boss, or FALSE if he don't. Only ONE word must be in the output.",
                    method=Contains(pattern="TRUE"),
                )),
                Tr(dst=dst.Current(), cnd=cnd.true()),
            ],
        },
        "boss_node": {
            RESPONSE: Message("Input your ID number."),
            TRANSITIONS: [
                Tr(dst="main_node", cnd=cnd.true()),
            ],
        },
        "latte_art_node": {
            # we can pass a node-specific prompt to a LLM.
            RESPONSE: llm_response(
                model_name="barista_model",
                prompt="PROMPT: pretend that you have never heard about latte art before and DO NOT answer the following questions. Instead ask a person about it.",
            ),
            TRANSITIONS: [Tr(dst="main_node", cnd=cnd.ExactMatch("Ok, goodbye."))],
        },
        "image_desc_node": {
            # we expect user to send some images of coffee.
            RESPONSE: llm_response(
                model_name="barista_model",
                prompt="PROMPT: user will give you some images of coffee. Describe them.",
            ),
            TRANSITIONS: [Tr(dst="main_node", cnd=cnd.true())],
        },
        "fallback_node": {
            RESPONSE: Message("I didn't quite understand you..."),
            TRANSITIONS: [Tr(dst="main_node", cnd=cnd.true())],
        },
    }
}

# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("main_flow", "start_node"),
    fallback_label=("main_flow", "fallback_node"),
    models={"barista_model": model},
)

if __name__ == "__main__":
    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
