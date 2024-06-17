from asyncio import get_event_loop
from typing import Any, Dict, List, Optional, Tuple, TypeAlias, Hashable

from pydantic import BaseModel

from dff.messengers.vk import PollingVKInterface
from dff.pipeline.types import PipelineRunnerFunction
from dff.script import Message
from dff.script.core.context import Context
from dff.script.core.message import DataAttachment

PathStep: TypeAlias = Tuple[Dict[str, Any], Message, Message, List[str]]

class MockVK(BaseModel, arbitrary_types_allowed=True):
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
    bot: MockVK
    happy_path: List[PathStep]
    interface: PollingVKInterface
    latest_ctx: Optional[Context] = None

    @classmethod
    def create(cls, interface: PollingVKInterface, happy_path: List[PathStep]) -> "MockApplication":
        instance = cls(bot=MockVK(), happy_path=happy_path, interface=interface)
        return instance

    def _wrap_pipeline_runner(self, runner: PipelineRunnerFunction):
        async def wrapped_pipeline_runner(
            message: Message, ctx_id: Optional[Hashable] = None, update_ctx_misc: Optional[dict] = None
        ) -> Context:
            self.latest_ctx = await runner(message, ctx_id, update_ctx_misc)
            return self.latest_ctx

        wrapped_pipeline_runner.is_wrapped = True
        wrapped_pipeline_runner.original = runner
        return wrapped_pipeline_runner

    def _wrap_populate_attachment(self, interface: PollingVKInterface):
        async def wrapped_populate_attachment(_: DataAttachment) -> bytes:
            return bytes()

        wrapped_populate_attachment.is_wrapped = True
        wrapped_populate_attachment.original = interface.populate_attachment
        return wrapped_populate_attachment

    def _run_bot(self) -> None:
        if not getattr(self.interface.pipeline_runner, "is_wrapped", False):
            self.interface.pipeline_runner = self._wrap_pipeline_runner(self.interface.pipeline_runner)
        if not getattr(self.interface.populate_attachment, "is_wrapped", False):
            self.interface.populate_attachment = self._wrap_populate_attachment(self.interface)

        loop = get_event_loop()
        for update, received, response, trace in self.happy_path:
            loop.run_until_complete(self.interface.on_message(update))
            assert self.latest_ctx is not None, "During pipeline runner execution, no context was produced!"
            assert self.latest_ctx.last_request == received, "Expected request message is not equal to expected!"
            assert self.latest_ctx.last_response == response, "Expected response message is not equal to expected!"
            assert self.bot.latest_trace == trace, "Expected trace is not equal to expected!"
            self.bot.latest_trace = list()
            self.latest_ctx = None

        self.interface.pipeline_runner = self.interface.pipeline_runner.original
        self.interface.populate_attachment = self.interface.populate_attachment.original

    def run_polling(self, poll_interval: float, timeout: int, allowed_updates: List[str]) -> None:
        return self._run_bot()
