from asyncio import get_event_loop
from typing import Any, Dict, Hashable, List, Optional, Tuple, TypeAlias
from pydantic import BaseModel

from telegram import File, Update
from telegram.ext import ExtBot

from dff.messengers.telegram.abstract import _AbstractTelegramInterface
from dff.script import Message
from dff.script.core.context import Context

PathStep: TypeAlias = Tuple[Dict, Message, Message, Tuple[str, Tuple, Dict]]


class MockBot(BaseModel):
    _original_bot: ExtBot
    _latest_trace: Optional[Tuple[str, Tuple, Dict]] = None

    async def get_file(self, file_id: str) -> File:
        return await self._original_bot.get_file(file_id)
    
    def __getattribute__(self, name: str) -> Any:
        def set_trace(*args, **kwargs):
            self._latest_trace = (name, args, kwargs)

        if hasattr(self, name):
            return super().__getattribute__(name)
        else:
            return set_trace


class MockApplication(BaseModel):
    mock_bot: MockBot
    happy_path: List[PathStep]
    _interface: _AbstractTelegramInterface
    _latest_ctx: Optional[Context] = None

    @classmethod
    def create(cls, interface: _AbstractTelegramInterface, happy_path: List[PathStep]) -> "MockApplication":
        mock_bot = MockBot(_original_bot=interface.application.bot)
        instance = cls(mock_bot=mock_bot, happy_path=happy_path, _interface=interface)
        interface.pipeline_runner = instance._wrapped_pipeline_runner
        return instance

    async def _wrapped_pipeline_runner(self, message: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None) -> Context:
        self._latest_ctx = await self._interface.pipeline_runner(message, ctx_id, update_ctx_misc)
        return self._latest_ctx

    def _run_bot(self) -> None:
        loop = get_event_loop()
        for update, received, response, trace in self.happy_path:
            if update["is_message"]:
                update = Update()
                loop.run_until_complete(self._interface.on_message(update, None))  # type: ignore
            else:
                update = Update()
                loop.run_until_complete(self._interface.on_callback(update, None))  # type: ignore
            assert self._latest_ctx is not None, "During pipeline runner execution, no context was produced!" 
            assert self._latest_ctx.last_request == received, "Expected request message is not equal to expected!"
            assert self._latest_ctx.last_response == response, "Expected response message is not equal to expected!"
            assert self.mock_bot._latest_trace == trace, "Expected trace is not equal to expected!"
            self.mock_bot._latest_trace = None
            self._latest_ctx = None

    def run_polling(self, poll_interval: float, timeout: int, allowed_updates: List[str]) -> None:
        return self._run_bot()

    def run_webhook(self, listen: str, port: str, allowed_updates: List[str]) -> None:
        return self._run_bot()
