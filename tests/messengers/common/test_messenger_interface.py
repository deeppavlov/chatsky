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


class BaseTestPollingInterface(PollingMessengerInterface):
    def __init__(self):
        self.obtained_updates = False
        self.requests = []
        self.expected_updates = []
        self.received_updates = []
        super().__init__()

    def not_obtained_updates(self):
        if len(self.received_updates) == len(self.expected_updates):
            self.obtained_updates = True
        return not self.obtained_updates

    def _get_updates(self):
        if len(self.requests) > 0:
            request = self.requests.pop(0)
            return [(request[0], Message(str(request[1])))]

    async def _respond(self, ctx_id, last_response):
        self.received_updates.append(str(last_response.text))


def test_echo_responses():
    # logger = logging.getLogger(__name__)
    # logging.basicConfig(level=logging.DEBUG, filename="test_log.log",filemode="w", format="%(asctime)s %(levelname)s %(message)s")
    class TestPollingInterface(BaseTestPollingInterface):
        def __init__(self):
            super().__init__()
            self.ctx_id = uuid.uuid4()
            self.requests = ["some request", "another request", "gkjln;s!", "foobarraboof"]
            self.expected_updates = self.requests.copy()
            self.received_updates = []
            self.obtained_updates = False

        def _get_updates(self):
            if len(self.requests) > 0:
                request = self.requests.pop(0)
                return [(self.ctx_id, Message(text=str(request)))]

    new_pipeline = Pipeline.from_script(
        ECHO_SCRIPT,
        start_label=("echo_flow", "start_node"),
        fallback_label=("echo_flow", "start_node"),
        messenger_interface=TestPollingInterface(),
    )
    interface = new_pipeline.messenger_interface
    asyncio.run(new_pipeline.messenger_interface.run_in_foreground(new_pipeline, loop=interface.not_obtained_updates))

    for i in range(4):
        assert interface.expected_updates[i] == interface.received_updates[i]
    assert interface.not_obtained_updates() == False


def test_context_lock():
    class TestPollingInterface(BaseTestPollingInterface):
        def __init__(self):
            super().__init__()
            self.obtained_updates = False
            self.requests = [(0, "id: 1"), (0, "id: 2"), (1, "id: 3")]
            self.expected_updates = [(0, "id: 1"), (1, "id: 3"), (0, "id: 2")]
            self.received_updates = []

        # First worker is ordered to hand over control to (0, id: 2), which immediately gives it back because of the ContextLock(). Then, id: 3 gets completed right away, due to there not being any more 'await' statements there.
        # What's important here is that the worker for the "id: 2" couldn't start working on it's task immediately, because of ContextLock(), proving it's function. Even though it was given control with an 'await' just below.
        async def _process_request(self, ctx_id, update: Message, pipeline: Pipeline):
            context = await pipeline._run_pipeline(update, ctx_id)
            if context.last_response.text == "id: 1":
                await asyncio.sleep(0)
            await self._respond(ctx_id, context.last_response)

    new_pipeline = Pipeline.from_script(
        ECHO_SCRIPT,
        start_label=("echo_flow", "start_node"),
        fallback_label=("echo_flow", "start_node"),
        messenger_interface=TestPollingInterface(),
    )
    interface = new_pipeline.messenger_interface
    asyncio.run(new_pipeline.messenger_interface.run_in_foreground(new_pipeline, loop=interface.not_obtained_updates))
    for i in range(3):
        assert interface.expected_updates[i][1] == interface.received_updates[i]
    assert interface.not_obtained_updates() == False
