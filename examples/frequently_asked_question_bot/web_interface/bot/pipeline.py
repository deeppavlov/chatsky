import os

from dff.pipeline import Pipeline
from dff.context_storages import context_storage_factory
from dff.messengers.telegram import PollingTelegramInterface

from .dialog_graph import script
from .pipeline_services import pre_services


db_uri = "postgresql+asyncpg://{}:{}@db:5432/{}".format(
    os.getenv("POSTGRES_USERNAME"),
    os.getenv("POSTGRES_PASSWORD"),
    os.getenv("POSTGRES_DB"),
)
db = context_storage_factory(db_uri)


def get_pipeline():
    interface_type = os.getenv("INTERFACE")
    telegram_token = os.getenv("TG_BOT_TOKEN")

    if interface_type == "telegram" and telegram_token is not None:
        messenger_interface = PollingTelegramInterface(token=telegram_token)
    elif interface_type == "web" or interface_type == "cli":
        messenger_interface = None
    else:
        raise RuntimeError(
            "INTERFACE environment variable must be set to one of the following:" "`telegram`, `web`, or `cli`."
        )

    pipeline: Pipeline = Pipeline.from_script(
        **script.pipeline_kwargs,
        messenger_interface=messenger_interface,
        context_storage=db,
        # pre-services run before bot sends a response
        pre_services=pre_services.services,
    )
    return pipeline


pipeline = get_pipeline()
