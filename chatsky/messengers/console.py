from typing import Any, Hashable, List, Optional, TextIO, Tuple
from uuid import uuid4
from chatsky.messengers.common.interface import PollingMessengerInterface
from chatsky.core.service.types import PipelineRunnerFunction
from chatsky.core.context import Context
from chatsky.core.message import Message


class CLIMessengerInterface(PollingMessengerInterface):
    """
    Command line message interface is the default message interface, communicating with user via `STDIN/STDOUT`.
    This message interface can maintain dialog with one user at a time only.
    """

    supported_request_attachment_types = set()
    supported_response_attachment_types = set()

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

    def _request(self) -> List[Tuple[Message, Any]]:
        return [(Message(text=input(self._prompt_request)), self._ctx_id)]

    def _respond(self, responses: List[Context]):
        print(f"{self._prompt_response}{responses[0].last_response}", file=self._descriptor)

    async def connect(self, pipeline_runner: PipelineRunnerFunction, **kwargs):
        """
        The CLIProvider generates new dialog id used to user identification on each `connect` call.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~chatsky.core.pipeline.Pipeline._run_pipeline` function.
        :param \\**kwargs: argument, added for compatibility with super class, it shouldn't be used normally.
        """
        self._ctx_id = uuid4()
        if self._intro is not None:
            print(self._intro)
        await super().connect(pipeline_runner, **kwargs)
