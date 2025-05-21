# %% [markdown]
"""
# LLM: 6. FewShot Example Prompt

This tutorial demonstrates how to use `FewShotExamplePrompt` to pass fewshot examples
to your LLM models inside Chatsky pipelines.

> This enables more controlled and instructive generation behaviors. We'll use a fictional "Book Advisor Bot" that gives literary suggestions based on theme.

"""

# %%
import os
from chatsky import (
    GLOBAL,
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    destinations as dst,
)
from chatsky.core.message import Message
from chatsky.utils.testing import is_interactive_mode
from chatsky.llm import LLM_API
from chatsky.responses.llm import LLMResponse
from chatsky.llm.prompt import FewShotExamplePrompt
from chatsky.llm.example_selector import Example, StaticExampleSelector
from langchain_openai import ChatOpenAI

openai_api_key = os.getenv("OPENAI_API_KEY")

model = LLM_API(
    ChatOpenAI(model="gpt-4o-mini", api_key=openai_api_key),
    system_prompt="You are a literary assistant helping users find books"
    "based on their genre or theme preferences.",
)

# %% [markdown]
"""
## Few-Shot Examples

We define a set of examples using `StaticExampleSelector` to guide the LLM in recommending books.
"""

# %%
examples = [
    Example(
        input="I'm into satirical sci-fi and magical institutions.",
        output="Recommendation: Try *Monday Begins on Saturday* by the Strugatsky brothers — witty, surreal, and clever.",
    ),
    Example(
        input="I want philosophical novels.",
        output="Recommendation: You may enjoy *The Picture of Dorian Gray* by Oscar Wilde — a haunting tale about beauty and morality.",
    ),
    Example(
        input="Looking for historical drama.",
        output="Recommendation: *War and Peace* by Leo Tolstoy is a profound choice — epic, emotional, and deeply human.",
    ),
    Example(
        input="I enjoy adventure and revenge.",
        output="Recommendation: Consider *The Count of Monte Cristo* by Alexandre Dumas — a masterful story of betrayal and redemption.",
    ),
    Example(
        input="Rural life and conflicts?",
        output="Recommendation: *And Quiet Flows the Don* by Mikhail Sholokhov — a vivid portrait of Cossack life and war.",
    ),
    Example(
        input="I'm into dark fantasy and mythology.",
        output="Recommendation: Check out *Lost Gods* by Brom — a gritty journey through the mythic underworld.",
    ),
]

example_selector = StaticExampleSelector(examples)

# %% [markdown]
"""
## Application Script

We define a two-part chatbot:
- `greeting_flow`: welcomes the user and handles routing
- `book_flow`: uses structured few-shot prompting for recommendations
"""

# %%
script = {
    GLOBAL: {
        TRANSITIONS: [
            Tr(dst=("greeting_flow", "start_node"), cnd=cnd.ExactMatch("/start")),
            Tr(dst=("book_flow", "recommend"), cnd=cnd.ExactMatch("/recommend")),
            Tr(dst=("book_flow", "recommend"), cnd=cnd.Regexp(".*")),
        ]
    },
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(
                "Hi! I'm BookBot.\n\n"
                "To get started:\n"
                "- Use /recommend to get a suggestion\n"
                "- Or tell me what kind of books you like"
            ),
            TRANSITIONS: [Tr(dst=("book_flow", "recommend"), cnd=cnd.Regexp(".*"))],
        },
        "fallback_node": {
            RESPONSE: Message(
                "Sorry, I didn’t get that. Try describing your book taste!"
            ),
            TRANSITIONS: [Tr(dst="start_node")],
        },
    },
    "book_flow": {
        "recommend": {
            RESPONSE: LLMResponse(
                llm_model_name="book_model",
                prompt=FewShotExamplePrompt(
                    examples=example_selector,
                    template="User theme: {input}\nBook: {output}",
                    prefix="You are a bookbot. Recommend only one relevant book for each theme.",
                    suffix="User theme: {input}\nBook:",
                    position=2,
                ),
            ),
            TRANSITIONS: [
                Tr(dst=("greeting_flow", "start_node"), cnd=cnd.ExactMatch("/end")),
                Tr(dst=dst.Current()),
            ],
        }
    },
}

# %%
pipeline = Pipeline(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    models={"book_model": model},
)

if __name__ == "__main__":
    if is_interactive_mode():
        pipeline.run()
