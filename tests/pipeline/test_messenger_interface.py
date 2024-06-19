import asyncio
import sys
import pathlib
import uuid

# Must be removed, used only for debug purposes
import logging

from dff.script import RESPONSE, TRANSITIONS, Message, Context
from dff.messengers.common import CLIMessengerInterface, CallbackMessengerInterface, PollingMessengerInterface
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
    asyncio.run(pipeline.messenger_interface.run_in_foreground(pipeline, loop=loop))
    # asyncio.run(pipeline.messenger_interface.connect(pipeline._run_pipeline, loop=loop))


def test_echo_responses():
    # logger = logging.getLogger(__name__)
    # logging.basicConfig(level=logging.DEBUG, filename="test_log.log",filemode="w", format="%(asctime)s %(levelname)s %(message)s")
    def repeat_message_back(ctx: Context, _: Pipeline, *args, **kwargs):
        return ctx.last_request
    ECHO_SCRIPT = {
        "echo_flow": {
            "start_node": {
                RESPONSE: repeat_message_back,
                TRANSITIONS: {"start_node": cnd.true()},
            },
        }
    }
    # (respond=request)

    """
    requests_queue = asyncio.Queue()
    for item in requests:
        requests_queue.put(item)
    """

    class TestCLIInterface(PollingMessengerInterface):
        def __init__(self):
            self.ctx_id = uuid.uuid4()
            self.requests = ["some request", "another request", "gkjln;s!", "foobarraboof"]
            self.requests_copy = self.requests.copy()
            self.received_updates = []
            # self.received_updates = self.requests.copy()
            self.obtained_updates = False
            self.count = 0
            super().__init__()

        def not_obtained_updates(self):
            if len(self.received_updates) == len(self.requests_copy):
                self.obtained_updates = True
            return not self.obtained_updates

        def _get_updates(self):
            print("_get_updates() called! ctx_id=", self.ctx_id)
            print("requests=", self.requests, ", received_updates=", self.received_updates)
            print("request_queue=", self.request_queue)
            if len(self.requests) > 0:
                return [(self.ctx_id, Message(text=str(self.requests.pop(0))))]
            else:
                pass
        async def _respond(self, ctx_id, last_response):
            print("response received!")
            self.received_updates.append(str(last_response.text))
            print("requests=", self.requests, ", received_updates=", self.received_updates, ", response=", last_response)

    new_pipeline = Pipeline.from_script(
        ECHO_SCRIPT,
        start_label=("echo_flow", "start_node"),
        fallback_label=("echo_flow", "start_node"),
        messenger_interface=TestCLIInterface()
    )
    interface = new_pipeline.messenger_interface
    """
    interface.obtained_updates = False
    print("before: ", interface.not_obtained_updates())
    interface.obtained_updates = True
    print("after: ", interface.not_obtained_updates())
    assert False
    """
    asyncio.run(new_pipeline.messenger_interface.run_in_foreground(new_pipeline, loop=interface.not_obtained_updates))
    print("run_in_foreground passed!")
    for i in range(4):
        assert interface.requests_copy[i] == interface.received_updates[i]
    assert interface.not_obtained_updates() == False
    """
    get_updates -> if not obtained_updates: [ctx_id, request]
    respond -> received_updates.append(ctx_id, response)
    
    new_pipeline.messenger_interface.connect(loop=not_obtained_updates)
    
    assert received_updates == expected
    """


def test_callback_messenger_interface(monkeypatch):
    interface = CallbackMessengerInterface()
    pipeline.messenger_interface = interface

    pipeline.run()

    for _ in range(0, 5):
        assert interface.on_request(Message("Ping"), 0).last_response == Message("Pong")
