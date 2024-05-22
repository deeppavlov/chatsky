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
from dff.pipeline import Pipeline
from dff.messengers.common.types import PollingInterfaceLoopFunction

if TYPE_CHECKING:
    from dff.pipeline.types import PipelineRunnerFunction

logger = logging.getLogger(__name__)


class MessengerInterface(abc.ABC):
    """
    Class that represents a message interface used for communication between pipeline and users.
    It is responsible for connection between user and pipeline, as well as for request-response transactions.
    """

    def __init__(self):
        self.task = None
        self.running_in_foreground = False

    @abc.abstractmethod
    async def connect(self, pipeline_runner: PipelineRunnerFunction):
        """
        Method invoked when message interface is instantiated and connection is established.
        May be used for sending an introduction message or displaying general bot information.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~dff.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        """
        raise NotImplementedError

    async def run_in_foreground(self, *args):
        self.running_in_foreground = True
        self.task = await asyncio.create_task(self.connect(args))
        await self.task
        # Allowing other interfaces (and all async tasks) to work too

    async def shutdown(self):
        await self.task.cancel()
        logger.info(f"{type(self).__name__} has stopped working - SIGINT received")


class PollingMessengerInterface(MessengerInterface):
    """
    Polling message interface runs in a loop, constantly asking users for a new input.
    """
    # Saved Pipeline() as a variable here. But it was said that it's going to be somewhere else due to MultipleInterfaces PR or Triggers PR (don't remember). That needs to be considered later, possibly using the connect() method or in some other way.
    # self.running seems very similar to self.running_in_foreground. Are they the same thing or not? Maybe not, because connect() can still be called by anyone without running in foreground, though very unlikely - most will use pipeline.run() calling run_in_foreground().
    def __init__(self):
        self.request_queue = asyncio.Queue()
        self.pipeline = None
        self.running = True
        super().__init__()

    @absractmethod
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
        await pipeline._run_pipeline(update, ctx_id)
        await self._respond(ctx_id, pipeline.last_response)

    async def _worker_job(self):
        """
        Obtain Lock over the current context,
        Process the update and send it.
        """
        # Is this the best order of the variables? They go in a different order in the pipeline._run_pipeline() arguments. Though this may be more logical.
        (ctx_id, update) = await self.request_queue.get()
        
        async with self.pipeline.context_lock[ctx_id]:  # get exclusive access to this context among interfaces
            await asyncio.to_thread(  # [optional] execute in a separate thread to avoid blocking
                self._process_request(ctx_id, update, self.pipeline)
            )

    async def _worker(self):
        while self.running or not self.request_queue.empty():
            await self._worker_job()

    @abstract
    async def _get_updates(self) -> list[tuple[ctx_id, update]]:
        """
        Obtain updates from another server

        Example:
            self.bot.request_updates()
        """

    async def _polling_job(self):
        async for update in self._get_updates():
            self.request_queue.put(update)

    async def _polling_loop(
        self,
        loop: PollingInterfaceLoopFunction = lambda: True,
        timeout: float = 0,
    ):
        while loop():
            await asyncio.shield(self._polling_job())  # shield from cancellation
            await asyncio.sleep(timeout)
        finally:
            self.running = False

    async def connect(
        self,
        pipeline: Pipeline,
        loop: PollingInterfaceLoopFunction = lambda: True,
        timeout: float = 0,
    ):
        self.pipeline = pipeline
        await asyncio.gather([self._polling_loop(loop=loop, timeout=timeout), shield(self._worker()), shield(self._worker())])

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

    # TODO: Change into _get_updates()
    # This method seems like it could just be renamed into _get_updates(), no? Just rearrange the parameters and this should work, I think. Though there would only be one update at a time with this implementation.
    def _request(self) -> List[Tuple[Message, Any]]:
        return [(Message(input(self._prompt_request)), self._ctx_id)]

    def _respond(self, ctx_id, last_response: Message):
        print(f"{self._prompt_response}{last_response.text()}", file=self._descriptor)

    async def connect(self, pipeline_runner: PipelineRunnerFunction, **kwargs):
        """
        The CLIProvider generates new dialog id used to user identification on each `connect` call.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~dff.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        :param \\**kwargs: argument, added for compatibility with super class, it shouldn't be used normally.
        """
        self._ctx_id = uuid.uuid4()
        if self._intro is not None:
            print(self._intro)
        await super().connect(pipeline_runner, **kwargs)
