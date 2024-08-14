# %% [markdown]
"""
# LLM: 3. Filtering History

If you want to take the messages that meet your particular criteria and pass them to the LLMs context you can use the `llm_response`s `filter_func` parameter.
It must be a function that takes a single `Message` object and returns a boolean.
"""

# %pip install chatsky[llm]

# %%
from chatsky.script import Message
from chatsky.script.conditions import exact_match
from chatsky.script.conditions import std_conditions as cnd
from chatsky.script import labels as lbl
from chatsky.script import RESPONSE, TRANSITIONS
from chatsky.pipeline import Pipeline
from chatsky.script import Context
from chatsky.utils.testing import (
    is_interactive_mode,
    run_interactive_mode,
)
from chatsky.llm.wrapper import LLM_API, llm_response
from chatsky.llm.filters import BaseFilter, FromTheModel

import os

os.environ["OPENAI_API_KEY"] = "<TOKEN>"

from langchain_openai import ChatOpenAI

# %%
model = LLM_API(
    ChatOpenAI(model="gpt-3.5-turbo"),
    system_prompt="You are a database assistant and must help your user to recover the demanded data from your memory.",
)

# %% [markdown]
"""
In this example we will use very simple filtering function to retrieve only the important messages.
"""


# %%
class FilterImportant(BaseFilter):
    def __call__(
        self,
        ctx: Context = None,
        request: Message = None,
        response: Message = None,
        model_name: str = None,
    ) -> bool:
        if "#important" in request.text.lower():
            return True
        return False


# %% [markdown]
"""
Alternatively, if you use several models in one script (e.g. one for chatting, one for text summarization), you may want to separate the models memory using the same `filter_func` parameter.
There is a function `FromTheModel` that can be used to separate the models memory.
"""
# %%
toy_script = {
    "main_flow": {
        "start_node": {
            RESPONSE: Message(""),
            TRANSITIONS: {"greeting_node": exact_match("Hi")},
        },
        "greeting_node": {
            RESPONSE: llm_response(model_name="assistant_model", history=0),
            TRANSITIONS: {"main_node": exact_match("Who are you?")},
        },
        "main_node": {
            RESPONSE: llm_response(model_name="assistant_model", history=3),
            TRANSITIONS: {
                "remind_node": cnd.exact_match("/remind"),
                lbl.repeat(): cnd.true(),
            },
        },
        "remind_node": {
            RESPONSE: llm_response(
                model_name="assistant_model",
                history=15,
                filter_func=FilterImportant,
            ),
            TRANSITIONS: {"main_node": cnd.true()},
        },
        "fallback_node": {
            RESPONSE: Message("I did not quite understand you..."),
            TRANSITIONS: {"main_node": cnd.true()},
        },
    }
}


# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("main_flow", "start_node"),
    fallback_label=("main_flow", "fallback_node"),
    models={"assistant_model": model},
)

if __name__ == "__main__":
    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
