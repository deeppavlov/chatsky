# %% [markdown]
"""
# LLM: 3. Filtering History

If you want to take the messages that meet your particular criteria and pass
them to the LLMs context you can use the `LLMResponse`s `filter_func` parameter.
It must be a function that takes a single `Message`
object and returns a boolean.
"""

# %pip install chatsky[llm] langchain-openai

# %%
from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    destinations as dst,
)
from langchain_ollama import ChatOllama
from chatsky.core.message import Message
from chatsky.utils.testing import is_interactive_mode
from chatsky.llm import LLM_API
from chatsky.responses.llm import LLMResponse
from chatsky.llm.filters import BaseHistoryFilter
from chatsky.core.context import Context


# %%
model = LLM_API(
    ChatOllama(model="phi3:instruct", temperature=0),
    system_prompt="You are a database assistant and must help your user to "
    "recover the demanded data from your memory. Act as a note keeper.",
)

# %% [markdown]
"""
Imagine having a bot for taking notes that will have a huge dialogue history.
In this example we will use very simple filtering function to
retrieve only the important messages from such a bot to use
context window more efficiently. Here, we can mart notes with "#important" tag
and then ask a bot to create a summary of all important messages using "/remind"
command.
If you want to learn more about filters see
[API ref](%doclink(api,llm.filters,BaseHistoryFilter)).
"""


# %%
class FilterImportant(BaseHistoryFilter):
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
Alternatively, if you use several models in one script
(e.g. one for chatting, one for text summarization),
you may want to separate the models memory
using the same `filter_func` parameter.
There is a function `FromModel` that
can be used to separate the models memory.
"""
# %%
toy_script = {
    "main_flow": {
        "start_node": {
            RESPONSE: Message(""),
            TRANSITIONS: [Tr(dst="greeting_node", cnd=cnd.ExactMatch("Hi"))],
        },
        "greeting_node": {
            RESPONSE: LLMResponse(model_name="note_model", history=0),
            TRANSITIONS: [
                Tr(dst="main_node", cnd=cnd.ExactMatch("Who are you?"))
            ],
        },
        "main_node": {
            RESPONSE: LLMResponse(model_name="note_model", history=3),
            TRANSITIONS: [
                Tr(dst="remind_node", cnd=cnd.ExactMatch("/remind")),
                Tr(dst=dst.Current()),
            ],
        },
        "remind_node": {
            RESPONSE: LLMResponse(
                model_name="assistant_note_modelmodel",
                prompt="Create a bullet list from all the previous "
                "messages tagged with #important.",
                history=15,
                filter_func=FilterImportant(),
            ),
            TRANSITIONS: [Tr(dst="main_node")],
        },
        "fallback_node": {
            RESPONSE: Message("I did not quite understand you..."),
            TRANSITIONS: [Tr(dst="main_node")],
        },
    }
}


# %%
pipeline = Pipeline(
    toy_script,
    start_label=("main_flow", "start_node"),
    fallback_label=("main_flow", "fallback_node"),
    models={"note_model": model},
)

if __name__ == "__main__":
    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        pipeline.run()  # This runs tutorial in interactive mode
