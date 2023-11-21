import os

from dff.messengers.telegram import PollingTelegramInterface
from dff.pipeline import Pipeline

from dialog_graph import script
from pipeline_services import pre_services


def get_pipeline(use_cli_interface: bool = False) -> Pipeline:
    telegram_token = os.getenv("TG_BOT_TOKEN")

    if use_cli_interface:
        messenger_interface = None
    elif telegram_token:
        messenger_interface = PollingTelegramInterface(token=telegram_token)
    else:
        raise RuntimeError(
            "Telegram token (`TG_BOT_TOKEN`) is not set. `TG_BOT_TOKEN` can be set via `.env` file."
            " For more info see README.md."
        )

    pipeline = Pipeline.from_script(
        script=script.script,
        start_label=("service_flow", "start_node"),
        fallback_label=("service_flow", "fallback_node"),
        messenger_interface=messenger_interface,
        # pre-services run before bot sends a response
        pre_services=pre_services.services,
    )

    return pipeline


if __name__ == "__main__":
    pipeline = get_pipeline()
    pipeline.run()
