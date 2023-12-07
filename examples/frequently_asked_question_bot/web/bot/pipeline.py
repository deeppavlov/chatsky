import os

from dff.pipeline import Pipeline
from dff.context_storages import context_storage_factory

from .dialog_graph import script
from .pipeline_services import pre_services


db_uri = "postgresql+asyncpg://{}:{}@db:5432/{}".format(
    os.getenv("POSTGRES_USERNAME"),
    os.getenv("POSTGRES_PASSWORD"),
    os.getenv("POSTGRES_DB"),
)
db = context_storage_factory(db_uri)

pipeline: Pipeline = Pipeline.from_script(
    **script.pipeline_kwargs,
    context_storage=db,
    # pre-services run before bot sends a response
    pre_services=pre_services.services,
)
