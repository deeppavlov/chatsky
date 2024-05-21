from asyncio import get_event_loop
from typing import Any, Hashable, List, Optional, Tuple, TypeAlias

from pydantic import BaseModel
from re import sub
from telegram import File, Update
from telegram.ext import ExtBot

from dff.messengers.telegram.abstract import _AbstractTelegramInterface
from dff.pipeline.types import PipelineRunnerFunction
from dff.script import Message
from dff.script.core.context import Context

PathStep: TypeAlias = Tuple[Update, Message, Message, List[str]]


def _compare_messages(mess1: Message, mess2: Message) -> bool:
    if mess1.text == None or mess2.text == None:
        return True
    m1 = mess1.model_copy(deep=True)
    m2 = mess2.model_copy(deep=True)
    m1.text = sub(r"`\d+`", "<<number>>", m1.text)
    m2.text = sub(r"`\d+`", "<<number>>", m2.text)
    return m1 == m2


class MockBot(BaseModel, arbitrary_types_allowed=True):
    original_bot: ExtBot
    latest_trace: List[str] = list()

    async def get_file(self, file_id: str) -> File:
        return await self.original_bot.get_file(file_id)

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
        mock_bot = MockBot(original_bot=interface.application.bot)
        instance = cls(bot=mock_bot, happy_path=happy_path, interface=interface)
        return instance

    def _wrap_pipeline_runner(self, runner: PipelineRunnerFunction):
        async def wrapped_pipeline_runner(
            message: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
        ) -> Context:
            self.latest_ctx = await runner(message, ctx_id, update_ctx_misc)
            return self.latest_ctx
        
        wrapped_pipeline_runner.is_wrapped = True
        return wrapped_pipeline_runner

    def _run_bot(self) -> None:
        if not getattr(self.interface.pipeline_runner, "is_wrapped", False):
            self.interface.pipeline_runner = self._wrap_pipeline_runner(self.interface.pipeline_runner)

        loop = get_event_loop()
        for update, received, response, trace in self.happy_path:
            if update.message is not None:
                loop.run_until_complete(self.interface.on_message(update, None))  # type: ignore
            elif update.callback_query is not None:
                loop.run_until_complete(self.interface.on_callback(update, None))  # type: ignore
            else:
                raise RuntimeError(f"Update {update} type unknown!")
            assert self.latest_ctx is not None, "During pipeline runner execution, no context was produced!"
            assert _compare_messages(self.latest_ctx.last_request, received), "Expected request message is not equal to expected!"
            assert _compare_messages(self.latest_ctx.last_response, response), "Expected response message is not equal to expected!"
            assert self.bot.latest_trace == trace, "Expected trace is not equal to expected!"
            self.bot.latest_trace = list()
            self.latest_ctx = None

    def run_polling(self, poll_interval: float, timeout: int, allowed_updates: List[str]) -> None:
        return self._run_bot()

    def run_webhook(self, listen: str, port: str, allowed_updates: List[str]) -> None:
        return self._run_bot()
