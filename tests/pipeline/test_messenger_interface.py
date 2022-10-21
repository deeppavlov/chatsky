import asyncio
import sys
import pathlib

import pytest

from dff.core.engine.core.keywords import RESPONSE, TRANSITIONS
from dff.core.pipeline import CLIMessengerInterface, Pipeline, CallbackMessengerInterface
import dff.core.engine.conditions as cnd

SCRIPT = {
    "pingpong_flow": {
        "start_node": {
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Ping")},
        },
        "node1": {
            RESPONSE: "Pong",
            TRANSITIONS: {"node1": cnd.exact_match("Ping")},
        },
        "fallback_node": {
            RESPONSE: "Ooops",
            TRANSITIONS: {"node1": cnd.exact_match("Ping")},
        },
    }
}

pipeline = Pipeline.from_script(
    SCRIPT,  # Actor script object, defined in `.utils` module.
    start_label=("pingpong_flow", "start_node"),
    fallback_label=("pingpong_flow", "fallback_node"),
)


def test_cli_messenger_interface(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: "Ping")
    sys.path.append(str(pathlib.Path(__file__).parent.absolute()))

    pipeline.messenger_interface = CLIMessengerInterface()

    def loop() -> bool:
        loop.runs_left -= 1
        return loop.runs_left >= 0

    loop.runs_left = 5

    # Literally what happens in pipeline.run()
    asyncio.run(pipeline.messenger_interface.connect(pipeline._run_pipeline, loop=loop))


def test_callback_messenger_interface(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda _: "Ping")
    sys.path.append(str(pathlib.Path(__file__).parent.absolute()))

    interface = CallbackMessengerInterface()
    pipeline.messenger_interface = interface

    # Literally what happens in pipeline.run()
    asyncio.run(pipeline.messenger_interface.connect(pipeline._run_pipeline))

    for _ in range(0, 5):
        assert interface.on_request("Ping", 0).last_response == "Pong"
