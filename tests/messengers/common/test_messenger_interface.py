import os
import signal
import asyncio
import sys
import pathlib
import uuid
import time

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

    async def _get_updates(self):
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

        async def _get_updates(self):
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


def test_worker_shielding():
    class TestPollingInterface(BaseTestPollingInterface):
        def __init__(self):
            super().__init__()
            self.ctx_id = uuid.uuid4()
            self.requests = ["1sa", "nb2", "3fdg", "g46", "2sh2", "h31", "m56", "72ds"]
            self.requests.extend(self.requests)
            self.requests.extend(self.requests)
            self.requests.extend(self.requests)
            self.requests.extend(self.requests)
            self.expected_updates = self.requests.copy()
            self.received_updates = []
            self.obtained_requests = False
            self.requests_count = 0

        def not_obtained_requests(self):
            if len(self.requests) == 0:
                self.obtained_requests = True
                print("hi")
                # This definitely doesn't call shutdown() for some reason
                # await self.shutdown()
                # or
                # self.shutdown()
                os.kill(os.getpid(), signal.SIGINT)
                """
                async_loop = asyncio.get_running_loop()
                async_loop.run_until_complete(self.shutdown())
                """
                # This shuts down the interface via the main method. The asyncio.CancelledError won't affect the workers due to shielding. If all the messages still get processed, then the workers are shielded.
            return True

        async def _get_updates(self):
            if len(self.requests) > 0:
                self.requests_count += 1
                request = self.requests.pop(0)
                return [(self.ctx_id, Message(text=str(request)))]

        async def _process_request(self, ctx_id, update: Message, pipeline: Pipeline):
            while self.running:
                await asyncio.sleep(0.05)
            context = await pipeline._run_pipeline(update, ctx_id)
            await self._respond(ctx_id, context.last_response)

        async def cleanup(self):
            await super().cleanup()
            pass
            # This is here, so that workers have a bit of time to complete the remaining requests.
            # Without this line the test fails, because there's nothing blocking the code further and the assertions execute immediately after.

    new_pipeline = Pipeline.from_script(
        ECHO_SCRIPT,
        start_label=("echo_flow", "start_node"),
        fallback_label=("echo_flow", "start_node"),
        messenger_interface=TestPollingInterface(),
    )
    interface = new_pipeline.messenger_interface
    asyncio.run(new_pipeline.messenger_interface.run_in_foreground(new_pipeline, loop=interface.not_obtained_requests))
    print(interface.expected_updates)
    print(interface.received_updates)
    for i in range(len(interface.expected_updates)):
        assert interface.expected_updates[i] == interface.received_updates[i]


def test_shielding():
    class TestPollingInterface(BaseTestPollingInterface):
        def __init__(self):
            super().__init__()
            self.ctx_id = uuid.uuid4()
            self.requests = ["1sa", "nb2", "3fdg", "g46", "2sh2", "h31", "m56", "72ds"]
            self.expected_updates = self.requests.copy()
            self.received_updates = []
            self.obtained_requests = False
            self.requests_count = 0

        def not_obtained_requests(self):
            if len(self.requests) == 0:
                self.obtained_requests = True
                print("hi")
                # This definitely doesn't call shutdown() for some reason
                # await self.shutdown()
                # or
                # self.shutdown()
                os.kill(os.getpid(), signal.SIGINT)
            return True

        async def _get_updates(self):
            if len(self.requests) > 0:
                self.requests_count += 1
                request = self.requests.pop(0)
                return [(self.ctx_id, Message(text=str(request)))]

        async def _process_request(self, ctx_id, update: Message, pipeline: Pipeline):
            while self.running:
                await asyncio.sleep(0.05)
            context = await pipeline._run_pipeline(update, ctx_id)
            await self._respond(ctx_id, context.last_response)

                # This shuts down the entire program via graceful termination. If the received messages are correct even after a SIGINT, the program has working graceful termination.
                # Ok, so it's interesting. When using time.sleep() graceful termination works, but when using an 'await asyncio.sleep()' the test breaks, because the exception from 'shutdown()' isn't caught. I couldn't figure it out, but now I think it's logical. When SIGINT is received by a new signal handler that I made, the program throws an exception into whichever async function it's currently in, could be any of them.

        async def cleanup(self):
            await super().cleanup()
            await asyncio.sleep(0.5)
            pass
            # This is here, so that workers have a bit of time to complete the remaining requests.
            # Without this line the test fails, because there's nothing blocking the code further and the assertions execute immediately after.

    new_pipeline = Pipeline.from_script(
        ECHO_SCRIPT,
        start_label=("echo_flow", "start_node"),
        fallback_label=("echo_flow", "start_node"),
        messenger_interface=TestPollingInterface(),
    )
    interface = new_pipeline.messenger_interface
    asyncio.run(new_pipeline.messenger_interface.run_in_foreground(new_pipeline, loop=interface.not_obtained_requests))
    print(interface.expected_updates)
    print(interface.received_updates)
    for i in range(len(interface.expected_updates)):
        assert interface.expected_updates[i] == interface.received_updates[i]
    assert interface.not_obtained_updates() == False
    assert interface.not_obtained_requests() == True


