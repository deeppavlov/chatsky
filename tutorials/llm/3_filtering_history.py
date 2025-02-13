# %% [markdown]
"""
# LLM: 3. Filtering History

If you want to pass only the messages that meet specific criteria to the LLM's
context, you can use the `filter_func` parameter in `LLMResponse`.
This parameter requires a class whose `call` method accepts the following
arguments: `context`, `request`, `response`, and `model_name`.

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
from langchain_openai import ChatOpenAI
from chatsky.core.message import Message
from chatsky.utils.testing import is_interactive_mode
from chatsky.llm import LLM_API
from chatsky.responses.llm import LLMResponse
from chatsky.llm.filters import BaseHistoryFilter
from chatsky.core.context import Context
import os

openai_api_key = os.getenv("OPENAI_API_KEY")

# %%
model = LLM_API(
    ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key),
    system_prompt="You are a database assistant and must help your user to "
    "recover the demanded data from your memory. Act as a note keeper.",
)

# %% [markdown]
"""
Imagine having a bot for taking notes that accumulates a large dialogue history.
In this example, we will use a simple filtering function to retrieve only the
important messages from such a bot, making the context window usage
more efficient. Here, we can mark notes with the `#important` tag and then ask
the bot to create a summary of all
important messages using the `/remind` command.

If you want to learn more about filters,
refer to the [API reference](%doclink(api,llm.filters,BaseHistoryFilter)).
"""


# %%
class FilterImportant(BaseHistoryFilter):
    def call(
        self,
        ctx: Context = None,
        request: Message = None,
        response: Message = None,
        llm_model_name: str = None,
    ) -> bool:
        if "#important" in request.text.lower():
            return True
        return False


# %% [markdown]
"""
Alternatively, if you use multiple models in one script
(e.g., one for chatting and another for text summarization),
you may want to separate the models' memory using the same `filter_func`
parameter. There is a function called `FromModel`
that can be used to achieve this separation.

Additionally, the `history` parameter in `LLMResponse` allows you to
specify the number of dialogue _turns_ that the model will use as history.
The default value is `5`.
"""
# %%
toy_script = {
    "main_flow": {
        "start_node": {
            RESPONSE: Message(""),
            TRANSITIONS: [Tr(dst="greeting_node", cnd=cnd.ExactMatch("Hi"))],
        },
        "greeting_node": {
            RESPONSE: LLMResponse(llm_model_name="note_model", history=0),
            TRANSITIONS: [
                Tr(dst="main_node", cnd=cnd.ExactMatch("Who are you?"))
            ],
        },
        "main_node": {
            RESPONSE: Message(
                "Hi! I am your note-taking assistant. "
                "Just send me your thoughts, and if you need to "
                "rewind a bit, send `/remind`, and I will provide "
                "a summary of your #important notes."
            ),
            TRANSITIONS: [
                Tr(dst="remind_node", cnd=cnd.ExactMatch("/remind")),
                Tr(dst=dst.Current()),
            ],
        },
        "remind_node": {
            RESPONSE: LLMResponse(
                llm_model_name="note_model",
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
