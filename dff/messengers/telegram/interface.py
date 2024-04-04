from telegram import Update

from dff.pipeline.types import PipelineRunnerFunction

from .abstract import _AbstractTelegramInterface


class PollingTelegramInterface(_AbstractTelegramInterface):  # pragma: no cover
    def __init__(self, token: str, interval: int = 2, timeout: int = 20) -> None:
        super().__init__(token)
        self.interval = interval
        self.timeout = timeout

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(pipeline_runner, *args, **kwargs)
        self.application.run_polling(
            poll_interval=self.interval, timeout=self.timeout, allowed_updates=Update.ALL_TYPES
        )


class CallbackTelegramInterface(_AbstractTelegramInterface):  # pragma: no cover
    def __init__(self, token: str, host: str = "localhost", port: int = 844):
        super().__init__(token)
        self.listen = host
        self.port = port

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(pipeline_runner, *args, **kwargs)
        self.application.run_webhook(listen=self.listen, port=self.port, allowed_updates=Update.ALL_TYPES)
