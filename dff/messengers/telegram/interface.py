from pathlib import Path
from typing import Hashable, List, Optional, Tuple
from telegram import Update

from dff.messengers.common.interface import PollingMessengerInterface, CallbackMessengerInterface
from dff.pipeline.types import PipelineRunnerFunction
from dff.script import Context, Message

from .abstract import _AbstractTelegramInterface


class PollingTelegramInterface(_AbstractTelegramInterface, PollingMessengerInterface):
    def __init__(
        self, token: str, attachments_directory: Optional[Path] = None, interval: int = 2, timeout: int = 20
    ) -> None:
        _AbstractTelegramInterface.__init__(self, token, attachments_directory)
        self.interval = interval
        self.timeout = timeout

    def _request(self) -> List[Tuple[Message, Hashable]]:
        raise RuntimeError("_request method for PollingTelegramInterface is not specified")

    def _respond(self, _: List[Context]):
        raise RuntimeError("_respond method for PollingTelegramInterface is not specified")

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(pipeline_runner, *args, **kwargs)
        self.application.run_polling(
            poll_interval=self.interval, timeout=self.timeout, allowed_updates=Update.ALL_TYPES
        )


class CallbackTelegramInterface(_AbstractTelegramInterface, CallbackMessengerInterface):
    def __init__(
        self, token: str, attachments_directory: Optional[Path] = None, host: str = "localhost", port: int = 844
    ):
        _AbstractTelegramInterface.__init__(self, token, attachments_directory)
        self.listen = host
        self.port = port

    def _request(self) -> List[Tuple[Message, Hashable]]:
        raise RuntimeError("_request method for CallbackTelegramInterface is not specified")

    def _respond(self, _: List[Context]):
        raise RuntimeError("_respond method for CallbackTelegramInterface is not specified")

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(pipeline_runner, *args, **kwargs)
        self.application.run_webhook(listen=self.listen, port=self.port, allowed_updates=Update.ALL_TYPES)
