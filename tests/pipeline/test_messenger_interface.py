import asyncio
import sys
import pathlib

from dff.script import RESPONSE, TRANSITIONS, Message
from dff.messengers.common import CLIMessengerInterface, CallbackMessengerInterface
from dff.pipeline import Pipeline
import dff.script.conditions as cnd

SCRIPT = {
    "pingpong_flow": {
        "start_node": {
            RESPONSE: {
                "text": "",
            },
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Ping"))},
        },
        "node1": {
            RESPONSE: {
                "text": "Pong",
            },
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Ping"))},
        },
        "fallback_node": {
            RESPONSE: {
                "text": "Ooops",
            },
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Ping"))},
        },
    }
}

pipeline = Pipeline.from_script(
    SCRIPT,
    start_label=("pingpong_flow", "start_node"),
    fallback_label=("pingpong_flow", "fallback_node"),
)


def test_cli_messenger_interface(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "Ping")
    sys.path.append(str(pathlib.Path(__file__).parent.absolute()))

    pipeline.messenger_interface = CLIMessengerInterface(intro="Hi, it's DFF powered bot, let's chat!")

    def loop() -> bool:
        loop.runs_left -= 1
        return loop.runs_left >= 0

    loop.runs_left = 5

    # Literally what happens in pipeline.run()
    asyncio.run(pipeline.messenger_interface.connect(pipeline._run_pipeline, loop=loop))


def test_callback_messenger_interface(monkeypatch):
    interface = CallbackMessengerInterface()
    pipeline.messenger_interface = interface

    pipeline.run()

    for _ in range(0, 5):
        assert interface.on_request(Message(text="Ping"), 0).last_response == Message(text="Pong")
