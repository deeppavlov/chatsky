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
import signal
import time # Don't forget to remove this
import contextlib

from typing import Optional, Any, List, Tuple, TextIO, Hashable, TYPE_CHECKING

from dff.script import Context, Message
from dff.messengers.common.types import PollingInterfaceLoopFunction

if TYPE_CHECKING:
    from dff.pipeline.types import PipelineRunnerFunction
    from dff.pipeline import Pipeline

logger = logging.getLogger(__name__)


class MessengerInterface(abc.ABC):
    """
    Class that represents a message interface used for communication between pipeline and users.
    It is responsible for connection between user and pipeline, as well as for request-response transactions.
    """

    def __init__(self):
        self.task = None
        self.running_in_foreground = False
        self.running = True
        self.stopped = False
        self.shielded = False # This determines whether the interface wants to be shut down with task.cancel() or just switching a flag. Let's say PollingMessengerInterface wants task.cancel()

    @abc.abstractmethod
    async def connect(self, *args):
        """
        Method invoked when message interface is instantiated and connection is established.
        May be used for sending an introduction message or displaying general bot information.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~dff.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        """
        raise NotImplementedError

# This is an optional method, so no need to make it abstract, I think.
    async def cleanup(self, *args):
        pass

    async def run_in_foreground(
        self, pipeline: Pipeline, loop: PollingInterfaceLoopFunction = lambda: True, timeout: float = 0, *args
    ):
        self.running_in_foreground = True
        self.pipeline = pipeline
        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, pipeline.sigint_handler)
        # TO-DO: Clean this up and/or think this through (connect() methods are different for various MessengerInterface() classes)
        if isinstance(self.pipeline.messenger_interface, PollingMessengerInterface):
            self.task = asyncio.create_task(self.connect(loop=loop, timeout=timeout, *args))
        elif isinstance(self.pipeline.messenger_interface, CallbackMessengerInterface):
            self.task = asyncio.create_task(self.connect(self.pipeline._run_pipeline, *args))
        else:
            self.task = asyncio.create_task(self.connect(self.pipeline._run_pipeline, *args))
        # await self.task
        #"""
        try:
            await self.task
        except asyncio.CancelledError:
            await self.cleanup()
        #"""
        # Allowing other interfaces (and all async tasks) to work too
        """
        with contextlib.suppress(asyncio.CancelledError):
            await self.task
        await asyncio.sleep(0)
        """
        self.stopped = True
       
        # Placeholder for any cleanup code.


    # I can make shutdown() work for PollingMessengerInterface, but I don't know the structure of Telegram Messenger Interfaces. Right now, this ends the main task and sets a flag self.running to False, so that any async tasks in loops can see that and turn off as soon as they are done.
    async def shutdown(self):
        logger.info(f"messenger_interface.shutdown() called - shutting down interface")
        self.running = False
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            # raise asyncio.CancelledError
            # await asyncio.sleep(0)
            if not self.stopped:
                raise asyncio.CancelledError

        """
        def raise_exception(signum, frame):
            raise ZeroDivisionError
        signal.signal(signal.SIGINT, raise_exception)
        """
        """
        print(self.task)
        self.task.cancel()
        # time.sleep(0.1)
        # await self.task
        """
        """

        print("this should've stopped")
        
        """
        """
        await asyncio.sleep(0)
        with contextlib.suppress(asyncio.CancelledError):
            await self.task
        await self.cleanup()
        """
        # raise HelloException
        
        # raise asyncio.CancelledError
        """
        self.task.cancel()
        await self.task
        """
        logger.info(f"{type(self).__name__} has stopped working - SIGINT received")


class PollingMessengerInterface(MessengerInterface):
    """
    Polling message interface runs in a loop, constantly asking users for a new input.
    """

    # self.running seems very similar to self.running_in_foreground. Are they the same thing or not? Maybe not, because connect() can still be called by anyone without running in foreground, though very unlikely - most will use pipeline.run() calling run_in_foreground().
    def __init__(self):
        self.request_queue = asyncio.Queue()
        self.shielded = True # Would like task.cancel()
        super().__init__()

    @abc.abstractmethod
    async def _respond(self, ctx_id, last_response):
        """
        Method used for sending users responses for their last input.

        :param ctx_id: Context id, specifies the user id. Without multiple messenger interfaces it's basically a redundant parameter, because this function is just a more complex `print(last_response)`. (Change before merge)
        :param last_response: Latest response from the pipeline which should be relayed to the specified user.
        """
        raise NotImplementedError

    async def _process_request(self, ctx_id, update: Message, pipeline: Pipeline):
        """
        Process a new update for ctx.
        """
        context = await pipeline._run_pipeline(update, ctx_id)
        await self._respond(ctx_id, context.last_response)

    async def _worker_job(self):
        """
        Obtain Lock over the current context,
        Process the update and send it.
        """
        request = await self.request_queue.get()
        if request is not None:
            (ctx_id, update) = request
            async with self.pipeline.context_lock[ctx_id]:  # get exclusive access to this context among interfaces
                # Trying to see if _process_request works at all. Looks like it does it just fine, actually
                await self._process_request(ctx_id, update, self.pipeline)
                # Doesn't work in a thread for some reason - it goes into an infinite cycle.
                """
                await asyncio.to_thread(  # [optional] execute in a separate thread to avoid blocking
                    self._process_request, ctx_id, update, self.pipeline
                )
                """
            return False
        else:
            return True

    async def _worker(self):
        while self.running or not self.request_queue.empty():
            no_more_jobs = await self._worker_job()
            if no_more_jobs:
                print("worker stopping")
                logger.info(f"Worker finished working - stop signal received and remaining requests have been processed.")
                break

    @abc.abstractmethod
    async def _get_updates(self) -> list[tuple[Any, Message]]:
        """
        Obtain updates from another server

        Example:
            self.bot.request_updates()
        """

    async def _polling_job(self, poll_timeout: float):
        try:
            coroutine = asyncio.wait_for(self._get_updates(), timeout=poll_timeout)
            received_updates = await coroutine
            if received_updates is not None:
                for update in received_updates:
                    await self.request_queue.put(update)
        except TimeoutError:
            # self.shutdown()
            # Shutting down is probably too extreme, unless it's several times in a row maybe.
            logger.info("polling_job failed - timed out")

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
            print("loop ending")
            logger.info(f"polling_loop stopped working - either the stop signal was received or the loop() condition was false.")
            # If there're no more jobs/stop signal received, a special 'None' request is sent to the queue (one for each worker), they shut down the workers.
            # In case of more workers than two, change the number of 'None' requests to the new number of workers.
            # for i in range(number_of_workers)
            for i in range(2):
                self.request_queue.put_nowait(None)

    async def connect(
        self,
        loop: PollingInterfaceLoopFunction = lambda: True,
        timeout: float = 0,
    ):
        #"""
        await asyncio.gather(
            self._polling_loop(loop=loop, timeout=timeout),
            asyncio.shield(self._worker()),
            asyncio.shield(self._worker()),
        )
        #"""
        """
        try:
            await asyncio.gather(
                self._polling_loop(loop=loop, timeout=timeout),
                asyncio.shield(self._worker()),
                asyncio.shield(self._worker()),
            )
        except asyncio.CancelledError:
            await self.cleanup()
            raise
        """

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

    def __init__(self):
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
    ):
        super().__init__()
        self._ctx_id: Optional[Hashable] = None
        self._intro: Optional[str] = intro
        self._prompt_request: str = prompt_request
        self._prompt_response: str = prompt_response
        self._descriptor: Optional[TextIO] = out_descriptor

    def _get_updates(self) -> List[Tuple[Any, Message]]:
        return [(self._ctx_id, Message(input(self._prompt_request)))]

    async def _respond(self, ctx_id, last_response: Message):
        print(f"{self._prompt_response}{last_response.text}", file=self._descriptor)

    async def connect(self, *args, **kwargs):
        """
        The CLIProvider generates new dialog id used to user identification on each `connect` call.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~dff.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        :param \\**kwargs: argument, added for compatibility with super class, it shouldn't be used normally.
        """
        self._ctx_id = uuid.uuid4()
        if self._intro is not None:
            print(self._intro)
        await super().connect(*args, **kwargs)
