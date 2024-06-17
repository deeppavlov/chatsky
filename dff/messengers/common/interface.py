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
from pathlib import Path
from tempfile import gettempdir
from typing import Optional, Any, List, Tuple, Hashable, TYPE_CHECKING, Type

if TYPE_CHECKING:
    from dff.script import Context, Message
    from dff.pipeline.types import PipelineRunnerFunction
    from dff.messengers.common.types import PollingInterfaceLoopFunction
    from dff.script.core.message import Attachment, DataAttachment

logger = logging.getLogger(__name__)


class MessengerInterface(abc.ABC):
    """
    Class that represents a message interface used for communication between pipeline and users.
    It is responsible for connection between user and pipeline, as well as for request-response transactions.
    """

    supported_request_attachment_types: set[Type[Attachment]] = set()
    supported_response_attachment_types: set[type[Attachment]] = set()

    def __init__(self, attachments_directory: Optional[Path] = None) -> None:
        tempdir = gettempdir()
        if attachments_directory is not None and not str(attachments_directory.absolute()).startswith(tempdir):
            self.attachments_directory = attachments_directory
        else:
            warning_start = f"Attachments directory for {type(self).__name__} messenger interface"
            warning_end = "attachment data won't be cached locally!"
            if attachments_directory is None:
                self.attachments_directory = Path(tempdir) / f"dff-cache-{type(self).__name__}"
                logger.warning(f"{warning_start} is None, so will be set to tempdir and {warning_end}")
            else:
                self.attachments_directory = attachments_directory
                logger.warning(f"{warning_start} is in tempdir, so {warning_end}")
        self.attachments_directory.mkdir(parents=True, exist_ok=True)

    @abc.abstractmethod
    async def connect(self, pipeline_runner: PipelineRunnerFunction):
        """
        Method invoked when message interface is instantiated and connection is established.
        May be used for sending an introduction message or displaying general bot information.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~dff.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        """
        raise NotImplementedError

    async def populate_attachment(self, attachment: DataAttachment) -> bytes:
        raise RuntimeError(f"Messanger interface {type(self).__name__} can't populate attachment {attachment}!")


class PollingMessengerInterface(MessengerInterface):
    """
    Polling message interface runs in a loop, constantly asking users for a new input.
    """

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

    def __init__(self, attachments_directory: Optional[Path] = None) -> None:
        super().__init__(attachments_directory)
        self._pipeline_runner: Optional[PipelineRunnerFunction] = None

    async def connect(self, pipeline_runner: PipelineRunnerFunction):
        self._pipeline_runner = pipeline_runner

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
