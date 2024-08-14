# %% [markdown]
"""
# LLM: 4. Structured Output

Sometimes, we want to output structured data, such as a valid JSON object or want to automatically fill particular fields in the output Message.
In Chatsky we can do that using Structured Output.
"""

# %pip install chatsky[llm]
# %%
from chatsky.script import Message
from chatsky.script.conditions import exact_match
from chatsky.script.conditions import std_conditions as cnd
from chatsky.script import labels as lbl
from chatsky.script import RESPONSE, TRANSITIONS, GLOBAL, LOCAL, MISC
from chatsky.pipeline import Pipeline
from chatsky.utils.testing import (
    is_interactive_mode,
    run_interactive_mode,
)
from chatsky.llm.wrapper import LLM_API, llm_response

from langchain_core.pydantic_v1 import BaseModel, Field

import os

os.environ["OPENAI_API_KEY"] = "<TOKEN>"

from langchain_openai import ChatOpenAI

# %% [markdown]
"""

"""
# %%
model = LLM_API(ChatOpenAI(model="gpt-3.5-turbo"))


class Movie(BaseModel):
    name: str = Field(description="Name of the movie")
    genre: str = Field(description="Genre of the movie")
    plot: str = Field(description="Plot of the movie in chapters")
    cast: list = Field(description="List of the actors")
