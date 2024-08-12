import pytest
import logging

from chatsky.core import Pipeline
from chatsky.core import Context


@pytest.fixture
def pipeline():
    return Pipeline(
        script={"flow": {"node1": {}, "node2": {}, "node3": {}}, "service": {"start": {}, "fallback": {}}},
        start_label=("service", "start"),
        fallback_label=("service", "fallback"),
    )


@pytest.fixture
def context_factory(pipeline):
    def _context_factory(forbidden_fields=None):
        ctx = Context.init(("service", "start"))
        ctx.framework_data.pipeline = pipeline
        if forbidden_fields is not None:

            class Forbidden:
                def __init__(self, name):
                    self.name = name

                class ForbiddenError(Exception):
                    pass

                def __getattr__(self, item):
                    raise self.ForbiddenError(f"{self.name!r} is forbidden")

            for forbidden_field in forbidden_fields:
                ctx.__setattr__(forbidden_field, Forbidden(forbidden_field))
        return ctx

    return _context_factory

@pytest.fixture
def log_event_catcher():
    def inner(logger, level=logging.DEBUG):
        logs = []

        class Handler(logging.Handler):
            def emit(self, record) -> bool:
                logs.append(record)
                return True

        logger.addHandler(Handler())
        logger.setLevel(level)
        return logs
    return inner
