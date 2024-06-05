from asyncio import get_event_loop
from contextlib import contextmanager
from typing import Any, Hashable, Iterator, List, Optional, Tuple, TypeAlias

from pydantic import BaseModel
from telegram import Update

from dff.messengers.telegram.abstract import _AbstractTelegramInterface
from dff.script import Message
from dff.script.core.context import Context
from dff.script.core.message import DataAttachment

PathStep: TypeAlias = Tuple[Update, Message, Message, List[str]]


class MockBot(BaseModel, arbitrary_types_allowed=True):
    latest_trace: List[str] = list()

    @staticmethod
    def representation(any: Any) -> str:
        if isinstance(any, bytes):
            return "<<bytes>>"
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
    def _check_context_and_trace(self, last_request: Message, last_response: Message, last_trace: List[str]) -> Iterator[None]:
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
    def _wrap_populate_attachment(self) -> Iterator[None]:
        async def wrapped_populate_attachment(_: DataAttachment) -> bytes:
            return bytes()

        original_populate_attachment = self.interface.populate_attachment
        self.interface.populate_attachment = wrapped_populate_attachment
        yield
        self.interface.populate_attachment = original_populate_attachment

    def _run_bot(self) -> None:
        loop = get_event_loop()
        with self._wrap_pipeline_runner(), self._wrap_populate_attachment():
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
