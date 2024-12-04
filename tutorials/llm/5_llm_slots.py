# %% [markdown]
"""
# LLM: 5. LLM Slots

If we want to retrieve some information from user input like name, address or
email we can simply use Chatsky's Slot system and user regexes or other formally
specified data retrieval techniques. But if the data is more finicky to get or
not explicitly presented in utterance we
encourage you to utilize Chatsky LLM Slots.
In this tutorial we will see how we can set up Slots that uses LLM's under
the hood to extract more obscure information from users input.
"""
# %pip install chatsky[llm] langchain-openai
# %%
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
from langchain_openai import ChatOpenAI

from chatsky.utils.testing import (
    is_interactive_mode,
)
from chatsky.slots.llm import LLMSlot, LLMGroupSlot
from chatsky.llm import LLM_API

import os

openai_api_key = os.getenv("OPENAI_API_KEY")

# %% [markdown]
"""
In this example we define LLM Group Slot with two LLM Slots in it.
Both of them can be used separately just as regular slots,
but if you are going to extract several LLM Slots simultaneously
we encourage you to put them in LLM Group Slot for optimization and convenience.

In the `LLMSlot.caption` parameter you should put description of a data piece
you want to retrieve. More specific descriptions will yield better results,
especially when using smaller models.

Note that we are passing the name of the model
 from pipeline.models dictionary to LLMGroupSlot.model field.

Also, as you can see we set `allow_partial_extraction` flag in "person" slot to
`True`. That will allow us to fill this template across multiple messages.
To see how to use partial extraction please address the
following tutorial %mddoclink(tutorial,llm.5_llm_slots).
"""

# %%
slot_model = LLM_API(
    ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key, temperature=0)
)

SLOTS = {
    "person": LLMGroupSlot(
        username=LLMSlot(caption="User's username in uppercase"),
        job=LLMSlot(caption="User's occupation, job, profession"),
        model="slot_model",
        allow_partial_extraction=True,
    )
}

script = {
    GLOBAL: {
        TRANSITIONS: [
            Tr(dst=("user_flow", "ask"), cnd=cnd.Regexp(r"^[sS]tart"))
        ]
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
        "start": {RESPONSE: "", TRANSITIONS: [Tr(dst=("user_flow", "ask"))]},
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
    start_label=("user_flow", "start"),
    fallback_label=("user_flow", "repeat_question"),
    slots=SLOTS,
    models={"slot_model": slot_model},
)


if __name__ == "__main__":
    if is_interactive_mode():
        pipeline.run()
