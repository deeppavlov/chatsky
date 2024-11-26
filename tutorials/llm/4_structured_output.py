# %% [markdown]
"""
# LLM: 4. Structured Output

Sometimes, we want to output structured data, such as a valid JSON object or
want to automatically fill particular fields in the output Message.
In Chatsky we can do that using Structured Output.
"""

# %pip install chatsky[llm] langchain-openai langchain-anthropic
# %%
import os
from chatsky import (
    TRANSITIONS,
    RESPONSE,
    GLOBAL,
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


from langchain_core.pydantic_v1 import BaseModel, Field



# %% [markdown]
"""
In this tutorial we will define two models.
"""
# %%
assistant_model = LLM_API(ChatOllama(model="llama3.2:1b", temperature=0))
movie_model = LLM_API(ChatOllama(model="kuqoi/qwen2-tools:latest", temperature=0))

# %% [markdown]
"""
For the structured output we will use two classes to show two possible ways of
using `message_schema` in responses.
The `Movie`, inherited from the `BaseModel` will act as a schema for the
response _text_, that will contain valid JSON containing desribed information.
The `ImportantMessage`, inherited from the `Message` class, will otherwise
define the fields of the output `Message`. In this example we will use this
to mark the message as important.
"""


# %%
class Movie(BaseModel):
    name: str = Field(description="Name of the movie")
    genre: str = Field(description="Genre of the movie")
    plot: str = Field(description="Plot of the movie in chapters")
    cast: list = Field(description="List of the actors")


class ImportantMessage(Message):
    text: str = Field(description="Text of the note")
    misc: dict = Field(
        description="A dictionary with 'important' "
        "key and true/false value in it"
    )


# %%

script = {
    GLOBAL: {
        TRANSITIONS: [
            Tr(
                dst=("greeting_flow", "start_node"),
                cnd=cnd.ExactMatch("/start"),
            ),
            Tr(dst=("movie_flow", "main_node"), cnd=cnd.ExactMatch("/movie")),
            Tr(dst=("note_flow", "main_node"), cnd=cnd.ExactMatch("/note")),
        ]
    },
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(),
        },
        "fallback_node": {
            RESPONSE: Message("I did not quite understand you..."),
            TRANSITIONS: [Tr(dst="start_node")],
        },
    },
    "movie_flow": {
        "main_node": {
            RESPONSE: LLMResponse(
                "movie_model",
                prompt="Ask user to request you for movie ideas.",
                message_schema=Movie,
            ),
            TRANSITIONS: [Tr(dst=dst.Current())],
        }
    },
    "note_flow": {
        "main_node": {
            RESPONSE: LLMResponse(
                "note_model",
                prompt="Help user take notes and mark the important ones.",
                message_schema=ImportantMessage,
            ),
            TRANSITIONS: [Tr(dst=dst.Current())],
        }
    },
}

# %%
pipeline = Pipeline(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    models={"movie_model": movie_model, "note_model": assistant_model},
)

if __name__ == "__main__":
    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        pipeline.run()  # This runs tutorial in interactive mode
