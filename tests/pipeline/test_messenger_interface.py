import asyncio
import sys
import pathlib

from dff.script import RESPONSE, TRANSITIONS, Message, Context
from dff.messengers.common import CLIMessengerInterface, CallbackMessengerInterface
from dff.pipeline import Pipeline
import dff.script.conditions as cnd

SCRIPT = {
    "pingpong_flow": {
        "start_node": {
            RESPONSE: {
                "text": "",
            },
            TRANSITIONS: {"node1": cnd.exact_match(Message("Ping"))},
        },
        "node1": {
            RESPONSE: {
                "text": "Pong",
            },
            TRANSITIONS: {"node1": cnd.exact_match(Message("Ping"))},
        },
        "fallback_node": {
            RESPONSE: {
                "text": "Ooops",
            },
            TRANSITIONS: {"node1": cnd.exact_match(Message("Ping"))},
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
    asyncio.run(pipeline.messenger_interface.run_in_foreground(pipeline, loop))
    # asyncio.run(pipeline.messenger_interface.connect(pipeline._run_pipeline, loop=loop))


def test_echo_responses():
    def repeat_message_back(ctx: Context, _: Pipeline, *args, **kwargs):
        return Message(ctx.last_request)
    ECHO_SCRIPT = {
        "echo_flow": {
            "start_node": {
                RESPONSE: repeat_message_back,
                TRANSITIONS: {"start_node": cnd.true()},
            },
        }
    }
    # (respond=request)

    obtained_updates = False
    received_updates = []
    def not_obtained_updates():
        return not obtained_updates
    class TestCLIInterface(CLIMessengerInterface):
        def _get_updates(self):
            if not_obtained_updates:
                return [ctx_id, request]
        def _respond(self, ctx_id, response):
            received_updates.append([ctx_id, response])

    new_pipeline = Pipeline.from_script(
        ECHO_SCRIPT,
        start_label=("echo_flow", "start_node"),
        fallback_label=("echo_flow", "start_node"),
        messenger_interface=TestCLIInterface()
    )
    asyncio.run(new_pipeline.messenger_interface.run_in_foreground(new_pipeline, not_obtained_updates))
    print(not_obtained_updates())
    assert not_obtained_updates() == False
    """
    get_updates -> if not obtained_updates: [ctx_id, request]
    respond -> received_updates.append(ctx_id, response)
    
    new_pipeline.messenger_interface.connect(loop=not_obtained_updates)
    
    assert received_updates == expected
    """
    assert True


def test_callback_messenger_interface(monkeypatch):
    interface = CallbackMessengerInterface()
    pipeline.messenger_interface = interface

    pipeline.run()

    for _ in range(0, 5):
        assert interface.on_request(Message("Ping"), 0).last_response == Message("Pong")
