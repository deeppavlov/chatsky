from typing import Any, Hashable, List, Optional, TextIO, Tuple
from uuid import uuid4
from chatsky.messengers.common.interface import PollingMessengerInterface
from chatsky.script.core.message import Message


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

    async def _get_updates(self) -> List[Tuple[Any, Message]]:
        return [(self._ctx_id, Message(input(self._prompt_request)))]

    async def _respond(self, ctx_id, last_response: Message):
        print(f"{self._prompt_response}{last_response.text}", file=self._descriptor)

    async def connect(self, *args, **kwargs):
        """
        The CLIProvider generates new dialog id used to user identification on each `connect` call.

        :param pipeline_runner: A function that should process user request and return context;
            usually it's a :py:meth:`~chatsky.pipeline.pipeline.pipeline.Pipeline._run_pipeline` function.
        :param \\**kwargs: argument, added for compatibility with super class, it shouldn't be used normally.
        """
        self._ctx_id = uuid4()
        if self._intro is not None:
            print(self._intro)
        await super().connect(*args, **kwargs)
