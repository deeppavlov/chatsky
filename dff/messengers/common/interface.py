"""
Message Interfaces
------------------
The Message Interfaces module contains several basic classes that define the message interfaces.
These classes provide a way to define the structure of the messengers that are used to communicate with the DFF.
"""

from __future__ import annotations
import abc
import asyncio
import logging
import uuid
from typing import Optional, Any, List, Tuple, TextIO, Hashable, TYPE_CHECKING

from dff.script import Context, Message
from dff.messengers.common.types import PollingInterfaceLoopFunction

if TYPE_CHECKING:
    from dff.pipeline.types import PipelineRunnerFunction

logger = logging.getLogger(__name__)


class MessengerInterface(abc.ABC):
    """
    Class that represents a message interface used for communication between pipeline and users.
    It is responsible for connection between user and pipeline, as well as for request-response transactions.
    """

    def __init__(self, name: Optional[str] = None):
        self.name = name if name is not None else str(type(self))


    @abc.abstractmethod
    async def connect(self, pipeline_runner: PipelineRunnerFunction, iface_id: str):
        """
        Method invoked when message interface is instantiated and connection is established.
        May be used for sending an introduction message or displaying general bot information.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~dff.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        """
        raise NotImplementedError


class PollingMessengerInterface(MessengerInterface):
    """
    Polling message interface runs in a loop, constantly asking users for a new input.
    """

    def __init__(self, name: Optional[str] = None):
        MessengerInterface.__init__(self, name)

    @abc.abstractmethod
    def _request(self) -> List[Tuple[Message, Hashable]]:
        """
        Method used for sending users request for their input.

        :return: A list of tuples: user inputs and context ids (any user ids) associated with the inputs.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _respond(self, responses: List[Context]):
        """
        Method used for sending users responses for their last input.

        :param responses: A list of contexts, representing dialogs with the users;
            `last_response`, `id` and some dialog info can be extracted from there.
        """
        raise NotImplementedError

    def _on_exception(self, e: BaseException):
        """
        Method that is called on polling cycle exceptions, in some cases it should show users the exception.
        By default, it logs all exit exceptions to `info` log and all non-exit exceptions to `error`.

        :param e: The exception.
        """
        if isinstance(e, Exception):
            logger.error(f"Exception in {type(self).__name__} loop!", exc_info=e)
        else:
            logger.info(f"{type(self).__name__} has stopped polling.")

    async def _polling_loop(
        self,
        pipeline_runner: PipelineRunnerFunction,
        timeout: float = 0,
    ):
        """
        Method running the request - response cycle once.
        """
        user_updates = self._request()
        responses = [await pipeline_runner(request, ctx_id) for request, ctx_id in user_updates]
        self._respond(responses)
        await asyncio.sleep(timeout)

    async def connect(
        self,
        pipeline_runner: PipelineRunnerFunction,
        iface_id: str,
        loop: PollingInterfaceLoopFunction = lambda: True,
        timeout: float = 0,
    ):
        """
        Method, running a request - response cycle in a loop.
        The looping behavior is determined by `loop` and `timeout`,
        for most cases the loop itself shouldn't be overridden.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~dff.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        :param loop: a function that determines whether polling should be continued;
            called in each cycle, should return `True` to continue polling or `False` to stop.
        :param timeout: a time interval between polls (in seconds).
        """
        self._interface_id = iface_id
        while loop():
            try:
                await self._polling_loop(pipeline_runner, timeout)

            except BaseException as e:
                self._on_exception(e)
                break


class CallbackMessengerInterface(MessengerInterface):
    """
    Callback message interface is waiting for user input and answers once it gets one.
    """

    def __init__(self, name: Optional[str] = None):
        self._pipeline_runner: Optional[PipelineRunnerFunction] = None
        MessengerInterface.__init__(self, name)

    async def connect(self, pipeline_runner: PipelineRunnerFunction, iface_id: str):
        self._pipeline_runner = pipeline_runner
        self._interface_id = iface_id

    async def on_request_async(
        self, request: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
    ) -> Context:
        """
        Method that should be invoked on user input.
        This method has the same signature as :py:class:`~dff.pipeline.types.PipelineRunnerFunction`.
        """
        return await self._pipeline_runner(request, ctx_id, update_ctx_misc)

    def on_request(
        self, request: Any, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
    ) -> Context:
        """
        Method that should be invoked on user input.
        This method has the same signature as :py:class:`~dff.pipeline.types.PipelineRunnerFunction`.
        """
        return asyncio.run(self.on_request_async(request, ctx_id, update_ctx_misc))


class CLIMessengerInterface(PollingMessengerInterface):
    """
    Command line message interface is the default message interface, communicating with user via `STDIN/STDOUT`.
    This message interface can maintain dialog with one user at a time only.
    """

    def __init__(
        self,
        intro: Optional[str] = None,
        prompt_request: str = "request: ",
        prompt_response: str = "response: ",
        out_descriptor: Optional[TextIO] = None,
        name: Optional[str] = None
    ):
        PollingMessengerInterface.__init__(self, name)
        self._ctx_id: Optional[Hashable] = None
        self._intro: Optional[str] = intro
        self._prompt_request: str = prompt_request
        self._prompt_response: str = prompt_response
        self._descriptor: Optional[TextIO] = out_descriptor

    def _request(self) -> List[Tuple[Message, Any]]:
        return [(Message(input(self._prompt_request), interface=self._interface_id), self._ctx_id)]

    def _respond(self, responses: List[Context]):
        print(f"{self._prompt_response}{responses[0].last_response_to(self._interface_id).text}", file=self._descriptor)

    async def connect(self, pipeline_runner: PipelineRunnerFunction, iface_id: str, **kwargs):
        """
        The CLIProvider generates new dialog id used to user identification on each `connect` call.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~dff.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        :param \\**kwargs: argument, added for compatibility with super class, it shouldn't be used normally.
        """
        self._ctx_id = uuid.uuid4()
        if self._intro is not None:
            print(self._intro)
        await super().connect(pipeline_runner, iface_id, **kwargs)
