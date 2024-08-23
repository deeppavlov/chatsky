"""
Message Interfaces
------------------
The Message Interfaces module contains several basic classes that define the message interfaces.
These classes provide a way to define the structure of the messengers that are used to communicate with Chatsky.
"""

from __future__ import annotations
import abc
import asyncio
import logging
from pathlib import Path
from tempfile import gettempdir

from typing import Optional, Any, Hashable, TYPE_CHECKING, Type
from pydantic import BaseModel

if TYPE_CHECKING:
    from chatsky.script import Context, Message
    from chatsky.pipeline.types import PipelineRunnerFunction
    from chatsky.messengers.common.types import PollingInterfaceLoopFunction
    from chatsky.script.core.message import Attachment
    from chatsky.pipeline.pipeline.pipeline import Pipeline

logger = logging.getLogger(__name__)


class MessengerInterface(abc.ABC, BaseModel):
    """
    Class that represents a message interface used for communication between pipeline and users.
    It is responsible for connection between user and pipeline, as well as for request-response transactions.
    """

    running: bool = True
    """Shows whether the interface is still accepting new requests."""
    finished_working: bool = False
    """Shows whether the interface has finished processing all of the requests received."""

    @abc.abstractmethod
    async def connect(
        self,
        pipeline_runner: PipelineRunnerFunction,
    ):
        """
        Method invoked when message interface is instantiated and connection is established.
        May be used for sending an introduction message or displaying general bot information.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~chatsky.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        """
        raise NotImplementedError

    async def cleanup(self):
        """
        A placeholder method for any cleanup code you want to be
        called before shutting down the program.
        You can redefine this method in your class.
        Note you also need to call cleanup() of the parent class.
        """
        pass


class MessengerInterfaceWithAttachments(MessengerInterface, abc.ABC):
    """
    MessengerInterface subclass that has methods for attachment handling.

    :param attachments_directory: Directory where attachments will be stored.
        If not specified, the temporary directory will be used.
    """

    supported_request_attachment_types: set[Type[Attachment]] = set()
    """
    Types of attachment that this messenger interface can receive.
    Attachments not in this list will be neglected.
    """

    supported_response_attachment_types: set[Type[Attachment]] = set()
    """
    Types of attachment that this messenger interface can send.
    Attachments not in this list will be neglected.
    """

    def __init__(self, attachments_directory: Optional[Path] = None) -> None:
        tempdir = gettempdir()
        if attachments_directory is not None and not str(attachments_directory.absolute()).startswith(tempdir):
            self.attachments_directory = attachments_directory
        else:
            warning_start = f"Attachments directory for {type(self).__name__} messenger interface"
            warning_end = "attachment data won't be cached locally!"
            if attachments_directory is None:
                self.attachments_directory = Path(tempdir) / f"chatsky-cache-{type(self).__name__}"
                logger.info(f"{warning_start} is None, so will be set to tempdir and {warning_end}")
            else:
                self.attachments_directory = attachments_directory
                logger.info(f"{warning_start} is in tempdir, so {warning_end}")
        self.attachments_directory.mkdir(parents=True, exist_ok=True)

    @abc.abstractmethod
    async def get_attachment_bytes(self, source: str) -> bytes:
        """
        Get attachment bytes from file source.

        E.g. if a file attachment consists of a URL of the file uploaded to the messenger servers,
        this method is the right place to call the messenger API for the file downloading.

        :param source: Identifying string for the file.
        :return: The attachment bytes.
        """
        raise NotImplementedError


class PollingMessengerInterface(MessengerInterface):
    """
    Polling message interface runs in a loop, constantly asking users for a new input.
    """
    number_of_workers: int = 2
    _request_queue = asyncio.Queue()
    _worker_tasks = []

    @abc.abstractmethod
    async def _respond(self, ctx_id, last_response):
        """
        Method used for sending users responses for their last input.

        :param ctx_id: Context id, specifies the user id. Without multiple messenger interfaces it's basically a
         redundant parameter, because this function is just a more complex `print(last_response)`. (Change before merge)
        :param last_response: Latest response from the pipeline which should be relayed to the specified user.
        """
        raise NotImplementedError

    async def _process_request(self, ctx_id: Any, update: Message, pipeline_runner: PipelineRunnerFunction):
        """Process a new update for ctx."""
        context = await pipeline_runner(update, ctx_id)
        await self._respond(ctx_id, context.last_response)

    async def _worker_job(self, pipeline_runner: PipelineRunnerFunction, worker_timeout: float):
        """
        Obtain Lock over the current context,
        Process the update and send it.
        """
        request = await self._request_queue.get()
        if request is not None:
            (ctx_id, update) = request
            async with self.pipeline.context_lock[ctx_id]:  # get exclusive access to this context among interfaces
                await asyncio.wait_for(
                    self._process_request(ctx_id, update, pipeline_runner),
                    timeout=worker_timeout,
                )
            return False
        else:
            return True

    # This worker doesn't save the request and basically deletes it from the queue in case it can't process it.
    # An option to save the request may be fitting? Maybe with an amount of retries.
    async def _worker(self, pipeline_runner: PipelineRunnerFunction, worker_timeout: float):
        while self.running or not self._request_queue.empty():
            try:
                no_more_jobs = self._worker_job(pipeline_runner, worker_timeout)
                if no_more_jobs:
                    logger.info("Worker finished working - all remaining requests have been processed.")
                    # Polling_loop should give the required data on whether the stop signal was sent or if
                    # the loop() function gave 'False'.
                    break
            except TimeoutError:
                logger.info("worker couldn't process request in time. A request *may* have been lost.")

    @abc.abstractmethod
    async def _get_updates(self) -> list[tuple[Any, Message]]:
        """
        Obtain updates from another server

        Example:
            self.bot.request_updates()
        """

    async def _polling_job(self, poll_timeout: float):
        try:
            received_updates = await asyncio.wait_for(self._get_updates(), timeout=poll_timeout)
            if received_updates is not None:
                for update in received_updates:
                    await self._request_queue.put(update)
        except TimeoutError:
            logger.debug("polling_job failed - timed out")

    async def _polling_loop(
        self,
        loop: PollingInterfaceLoopFunction = lambda: True,
        poll_timeout: float = None,
        timeout: float = 0,
    ):
        try:
            while loop() and self.running:
                await asyncio.shield(self._polling_job(poll_timeout))  # shield from cancellation
                await asyncio.sleep(timeout)
        finally:
            self.running = False
            # If loop() is somehow True after being False once, this logging will be wrong.
            # But no user would want to break their own logging, right?
            if loop() is False:
                logger.info("polling_loop stopped working - the loop() condition was False")
            else:
                logger.info("polling_loop stopped working - the stop signal was received.")
            # If there are no more jobs/stop signal received, a special 'None' request is
            # sent to the queue (one for each worker), they shut down the workers.
            # In case of more workers than two, change the number of 'None' requests to the new number of workers.
            for i in range(self.number_of_workers):
                self._request_queue.put_nowait(None)

    async def connect(
        self,
        pipeline_runner: PipelineRunnerFunction,
        loop: PollingInterfaceLoopFunction = lambda: True,
        poll_timeout: float = None,
        worker_timeout: float = None,
        timeout: float = 0,
    ):
        # Saving strong references to workers, so that they can be cleaned up properly.
        # shield() creates a task just like create_task() according to docs.
        # But for safety we have two task wrappers, I guess.
        for i in range(self.number_of_workers):
            task = asyncio.create_task(asyncio.shield(self._worker(pipeline_runner, worker_timeout)))
            self._worker_tasks.append(task)
        print("worker tasks:", self._worker_tasks)
        await self._polling_loop(loop=loop, poll_timeout=poll_timeout, timeout=timeout)

    # Maybe "worker_cleanup" instead of this function name?
    async def cleanup(self):
        """
        Blocks until all workers are done.
        """
        await super().cleanup()
        await asyncio.wait(self._worker_tasks)

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


class CallbackMessengerInterface(MessengerInterface):
    """
    Callback message interface is waiting for user input and answers once it gets one.
    """

    def __init__(self) -> None:
        self._pipeline_runner: Optional[PipelineRunnerFunction] = None
        super().__init__()

    async def connect(
        self,
        pipeline_runner: PipelineRunnerFunction,
    ):
        self._pipeline_runner = pipeline_runner

    async def on_request_async(
        self, request: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
    ) -> Context:
        """
        Method that should be invoked on user input.
        This method has the same signature as :py:class:`~chatsky.pipeline.types.PipelineRunnerFunction`.
        """
        return await self._pipeline_runner(request, ctx_id, update_ctx_misc)

    def on_request(
        self, request: Any, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
    ) -> Context:
        """
        Method that should be invoked on user input.
        This method has the same signature as :py:class:`~chatsky.pipeline.types.PipelineRunnerFunction`.
        """
        return asyncio.run(self.on_request_async(request, ctx_id, update_ctx_misc))
