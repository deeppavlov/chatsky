from chatsky.script import Message
from chatsky.script.conditions import exact_match
from chatsky.script.conditions import std_conditions as cnd
from chatsky.script import RESPONSE, TRANSITIONS
from chatsky.pipeline import Pipeline
from chatsky.utils.testing import (
    is_interactive_mode,
    run_interactive_mode,
)
from chatsky.llm.wrapper import LLM_API, llm_response
from chatsky.messengers.telegram import LongpollingInterface

import getpass
import os

from langchain_openai import ChatOpenAI

model = LLM_API(model=ChatOpenAI(model="gpt-3.5-turbo", api_key="sk-or-vv-06d82e66f904542017a7bbace5efe7669ab0cd599424a21a6b3d976b7e33ed6d", base_url="https://api.vsegpt.ru/v1"),
                system_prompt="You are an experienced barista in a local coffeshop. Answer your customers questions about coffee and barista work.")

toy_script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(""),
            TRANSITIONS: {"greeting_node": exact_match("Hi")},
        },
        "greeting_node": {
            RESPONSE: llm_response(model_name="barista_model", history=0),
            TRANSITIONS: {"main_node": exact_match("i'm fine, how are you?")},
        },
        "main_node": {
            RESPONSE: llm_response(model_name="barista_model"),
            TRANSITIONS: {
                "latte_art_node": exact_match("Tell me about latte art."),
                "image_desc_node": exact_match("Tell me what coffee is it?")},
        },
        "latte_art_node": {
            RESPONSE: llm_response(model_name="barista_model", prompt="PROMPT: pretend that you have never heard about latte art before."),
            TRANSITIONS: {"image_desc_node": exact_match("Ok, goodbye.")},
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

interface = LongpollingInterface(token="6075571274:AAF7K1wW8qQt-9RmlUS6RMQnvmU75nyrgWw")

pipeline = Pipeline.from_script(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,
    models={"barista_model": model}
)

if __name__ == "__main__":
    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        pipeline.run()

