import asyncio
import sys
import pathlib

from chatsky.core import RESPONSE, TRANSITIONS, Message, Pipeline, Transition as Tr
from chatsky.messengers.console import CLIMessengerInterface
from chatsky.messengers.common import CallbackMessengerInterface
import chatsky.conditions as cnd

SCRIPT = {
    "pingpong_flow": {
        "start_node": {
            TRANSITIONS: [Tr(dst="node1", cnd=cnd.ExactMatch("Ping"))],
        },
        "node1": {
            RESPONSE: "Pong",
            TRANSITIONS: [Tr(dst="node1", cnd=cnd.ExactMatch("Ping"))],
        },
        "fallback_node": {
            RESPONSE: "Ooops",
            TRANSITIONS: [Tr(dst="node1", cnd=cnd.ExactMatch("Ping"))],
        },
    }
}

pipeline = Pipeline(
    script=SCRIPT,
    start_label=("pingpong_flow", "start_node"),
    fallback_label=("pingpong_flow", "fallback_node"),
)


def test_cli_messenger_interface(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "Ping")
    sys.path.append(str(pathlib.Path(__file__).parent.absolute()))

    pipeline.messenger_interface = CLIMessengerInterface(intro="Hi, it's Chatsky powered bot, let's chat!")

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
