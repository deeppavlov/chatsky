from asyncio import get_event_loop
from contextlib import contextmanager
from importlib import import_module
from hashlib import sha256
from typing import Any, Dict, Hashable, Iterator, List, Optional, Tuple, Union

from pydantic import BaseModel
from telegram import InputFile, InputMedia, Update
from typing_extensions import TypeAlias

from chatsky.messengers.telegram.abstract import _AbstractTelegramInterface
from chatsky.script import Message
from chatsky.script.core.context import Context

PathStep: TypeAlias = Tuple[Update, Message, Message, List[str]]


def cast_dict_to_happy_step(dictionary: Dict, update_only: bool = False) -> Union[List["PathStep"]]:
    imports = globals().copy()
    imports.update(import_module("telegram").__dict__)
    imports.update(import_module("telegram.ext").__dict__)
    imports.update(import_module("telegram.constants").__dict__)

    path_steps = list()
    for step in dictionary:
        update = eval(step["update"], imports)
        if not update_only:
            received = Message.model_validate(step["received_message"])
            received.original_message = update
            response = Message.model_validate(step["response_message"])
            path_steps += [(update, received, response, step["response_functions"])]
        else:
            path_steps += [(update, Message(), Message(), list())]
    return path_steps


class MockBot(BaseModel, arbitrary_types_allowed=True):
    latest_trace: List[str] = list()

    @staticmethod
    def representation(any: Any) -> str:
        if isinstance(any, InputFile):
            return sha256(any.input_file_content).hexdigest()
        elif isinstance(any, InputMedia):
            data = MockBot.representation(any.media) if isinstance(any.media, InputFile) else "<<bytes>>"
            return f"{type(any).__name__}(data='{data}', type={any.type.__repr__()})"
        elif isinstance(any, bytes):
            return sha256(any).hexdigest().__repr__()
        elif isinstance(any, list):
            return f"[{', '.join([MockBot.representation(a) for a in any])}]"
        else:
            return any.__repr__()

    def __getattribute__(self, name: str) -> Any:
        async def set_trace(*args, **kwargs):
            joined_args = ", ".join([self.representation(a) for a in args])
            joined_kwargs = ", ".join([f"{k}={self.representation(v)}" for k, v in kwargs.items()])
            arguments = ", ".join([joined_args, joined_kwargs])
            self.latest_trace += [f"{name}({arguments})"]

        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return set_trace


class MockApplication(BaseModel, arbitrary_types_allowed=True):
    bot: MockBot
    happy_path: List[PathStep]
    interface: _AbstractTelegramInterface
    latest_ctx: Optional[Context] = None

    @classmethod
    def create(cls, interface: _AbstractTelegramInterface, happy_path: List[PathStep]) -> "MockApplication":
        instance = cls(bot=MockBot(), happy_path=happy_path, interface=interface)
        return instance

    @contextmanager
    def _check_context_and_trace(
        self, last_request: Message, last_response: Message, last_trace: List[str]
    ) -> Iterator[None]:
        self.bot.latest_trace = list()
        self.latest_ctx = None
        yield
        assert self.latest_ctx is not None, "During pipeline runner execution, no context was produced!"
        assert self.latest_ctx.last_request == last_request, "Expected request message is not equal to expected!"
        assert self.latest_ctx.last_response == last_response, "Expected response message is not equal to expected!"
        assert self.bot.latest_trace == last_trace, "Expected trace is not equal to expected!"

    @contextmanager
    def _wrap_pipeline_runner(self) -> Iterator[None]:
        original_pipeline_runner = self.interface._pipeline_runner

        async def wrapped_pipeline_runner(
            message: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
        ) -> Context:
            self.latest_ctx = await original_pipeline_runner(message, ctx_id, update_ctx_misc)
            return self.latest_ctx

        self.interface._pipeline_runner = wrapped_pipeline_runner
        yield
        self.interface._pipeline_runner = original_pipeline_runner

    @contextmanager
    def _wrap_get_attachment_bytes(self) -> Iterator[None]:
        async def wrapped_get_attachment_bytes(source: str) -> bytes:
            return source.encode()

        original_populate_attachment = self.interface.get_attachment_bytes
        self.interface.get_attachment_bytes = wrapped_get_attachment_bytes
        yield
        self.interface.get_attachment_bytes = original_populate_attachment

    def _run_bot(self) -> None:
        loop = get_event_loop()
        with self._wrap_pipeline_runner(), self._wrap_get_attachment_bytes():
            for update, received, response, trace in self.happy_path:
                with self._check_context_and_trace(received, response, trace):
                    if update.message is not None:
                        loop.run_until_complete(self.interface.on_message(update, None))  # type: ignore
                    elif update.callback_query is not None:
                        loop.run_until_complete(self.interface.on_callback(update, None))  # type: ignore
                    else:
                        raise RuntimeError(f"Update {update} type unknown!")

    def run_polling(self, poll_interval: float, timeout: int, allowed_updates: List[str]) -> None:
        return self._run_bot()

    def run_webhook(self, listen: str, port: str, allowed_updates: List[str]) -> None:
        return self._run_bot()
