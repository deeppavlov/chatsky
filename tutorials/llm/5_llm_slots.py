# %% [markdown]
"""
# LLM: 5. LLM Slots

When we need to retrieve specific information from user input such as a name,
address, or email we can use Chatsky's Slot system along with regexes or other
formally specified data retrieval techniques.

However, if the data is more nuanced or not explicitly stated in the user's
utterance, we recommend using Chatsky's **LLM Slots**.

In this tutorial, we will explore how to set up Slots that leverage LLMs
to extract more complex or implicit information from user input.
"""
# %pip install chatsky[llm] langchain-openai
# %%
import os

from chatsky import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITION,
    GLOBAL,
    LOCAL,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    processing as proc,
    responses as rsp,
)

from chatsky.utils.testing import (
    is_interactive_mode,
)
from chatsky.slots.llm import LLMSlot, LLMGroupSlot
from chatsky.llm import LLM_API
from langchain_openai import ChatOpenAI

openai_api_key = os.getenv("OPENAI_API_KEY")

# %% [markdown]
"""
In this example, we define an **LLM Group Slot** containing two **LLM Slots**.
While these slots can be used independently as regular slots,
grouping them together is recommended when extracting multiple LLM Slots
simultaneously. This approach optimizes performance and improves convenience.

- In the `LLMSlot.caption` parameter, provide a description of the data you
want to retrieve. More specific descriptions yield better results,
especially when using smaller models.
- Pass the name of the model from the `pipeline.models`
dictionary to the `LLMGroupSlot.model` field.
- Additionally, the `allow_partial_extraction` flag is set to `True` for the
"person" slot. This allows the slot to be filled across multiple messages.
For more details on partial extraction,
refer to the tutorial: %mddoclink(tutorial,slots.2_partial_extraction).
"""

# %%
slot_model = LLM_API(
    ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0)
)

SLOTS = {
    "person": LLMGroupSlot(
        username=LLMSlot(caption="User's username in uppercase"),
        job=LLMSlot(caption="User's occupation, job, profession"),
        llm_model_name="slot_model",
        allow_partial_extraction=True,
    )
}

script = {
    GLOBAL: {
        TRANSITIONS: [
            Tr(dst=("user_flow", "ask"), cnd=cnd.Regexp(r"^[sS]tart"))
        ]
    },
    "start_flow": {
        "start": {RESPONSE: "", TRANSITIONS: [Tr(dst=("user_flow", "ask"))]},
    },
    "user_flow": {
        LOCAL: {
            PRE_TRANSITION: {"get_slot": proc.Extract("person")},
            TRANSITIONS: [
                Tr(
                    dst=("user_flow", "tell"),
                    cnd=cnd.SlotsExtracted("person"),
                    priority=1.2,
                ),
                Tr(dst=("user_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {
            RESPONSE: "Hello! Tell me about yourself: what are you doing for "
            "the living or your hobbies. "
            "And don't forget to introduce yourself!",
        },
        "tell": {
            RESPONSE: rsp.FilledTemplate(
                "So you are {person.username} and your "
                "occupation is {person.job}, right?"
            ),
            TRANSITIONS: [Tr(dst=("user_flow", "ask"))],
        },
        "repeat_question": {
            RESPONSE: "I didn't quite understand you...",
        },
    },
}

pipeline = Pipeline(
    script=script,
    start_label=("start_flow", "start"),
    fallback_label=("user_flow", "repeat_question"),
    slots=SLOTS,
    models={"slot_model": slot_model},
)


if __name__ == "__main__":
    if is_interactive_mode():
        pipeline.run()
