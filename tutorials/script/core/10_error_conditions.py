# %% [markdown]
"""
# Core: 10. Error conditions
"""

# %pip install dff

# %%
from typing import Type
from dff.script import GLOBAL, TRANSITIONS, RESPONSE, Context, Message
from dff.pipeline import PIPELINE_EXCEPTION_KEY, LATEST_EXCEPTION_KEY, LATEST_FAILED_NODE_KEY, Pipeline
import dff.script.conditions as cnd
import dff.script.labels as lbl

from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)


def raise_exception(exception_class: Type[BaseException]) -> Message:
    raise exception_class("Some evil cause!")


def print_exception(name: str, _: Pipeline, ctx: Context) -> Message:
    exception = ctx.framework_states[PIPELINE_EXCEPTION_KEY].get(LATEST_EXCEPTION_KEY, None)
    message = "UNKNOWN" if exception is None else str(exception)
    source = ctx.framework_states[PIPELINE_EXCEPTION_KEY].get(LATEST_FAILED_NODE_KEY, None)
    return Message(f"Exception type {name} with message '{message}' received from node {source}!")


# %%
toy_script = {
    GLOBAL: {
        TRANSITIONS: {
            ("error_flow", "node_name_handler", 1.1): NameError,
            ("error_flow", "node_buffer_handler", 1.1): BufferError,
        },
    },
    "error_flow": {
        "start_node": {
            RESPONSE: Message(),
            TRANSITIONS: {
                "node_start_exceptor": cnd.exact_match(Message("start")),
            },
        },
        "node_start_exceptor": {
            RESPONSE: Message("Select an exception to throw!"),
            TRANSITIONS: {
                "node_name_thrower": cnd.exact_match(Message("name")),
                "node_buffer_thrower": cnd.exact_match(Message("buffer")),
                "node_file_thrower": cnd.exact_match(Message("fallback")),
            },
        },
        "node_name_thrower": {
            RESPONSE: lambda _, __: raise_exception(NameError),
        },
        "node_buffer_thrower": {
            RESPONSE: lambda _, __: raise_exception(BufferError),
        },
        "node_file_thrower": {
            RESPONSE: lambda _, __: raise_exception(FileNotFoundError),
        },
        "node_name_handler": {
            RESPONSE: lambda ctx, pipeline: print_exception("Name Error", pipeline, ctx),
            TRANSITIONS: {
                "node_start_exceptor": cnd.exact_match(Message("okay...")),
            },
        },
        "node_buffer_handler": {
            RESPONSE: lambda ctx, pipeline: print_exception("Buffer Error", pipeline, ctx),
            TRANSITIONS: {
                "node_start_exceptor": cnd.exact_match(Message("okay...")),
            },
        },
        "fallback_node": {
            RESPONSE: Message(f"Unexpected message received or an unknown exception caught!"),
            TRANSITIONS: {
                "node_start_exceptor": cnd.exact_match(Message("okay...")),
            },
        },
    }
}


happy_path = (
    (
        Message("start"),
        Message("Select an exception to throw!"),
    ),
    (
        Message("name"),
        Message("Exception type Name Error with message 'Some evil cause!' received from node actor_0:error_flow:node_name_thrower!"),
    ),
    (
        Message("okay..."),
        Message("Select an exception to throw!"),
    ),
    (
        Message("buffer"),
        Message("Exception type Buffer Error with message 'Some evil cause!' received from node actor_0:error_flow:node_buffer_thrower!"),
    ),
    (
        Message("okay..."),
        Message("Select an exception to throw!"),
    ),
    (
        Message("fallback"),
        Message("Unexpected message received or an unknown exception caught!"),
    ),
    (
        Message("okay..."),
        Message("Select an exception to throw!"),
    ),
    (
        Message("something"),
        Message("Unexpected message received or an unknown exception caught!"),
    ),
)


# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("error_flow", "start_node"),
    fallback_label=("error_flow", "fallback_node"),
    validation_stage=False,
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)

# %%
