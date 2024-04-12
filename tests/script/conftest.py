import pytest

from dff.pipeline import Pipeline
from dff.script import Context


@pytest.fixture
def pipeline():
    return Pipeline.from_script(
        script={"flow": {"node1": {}, "node2": {}, "node3": {}}, "service": {"start": {}, "fallback": {}}},
        start_label=("service", "start"),
        fallback_label=("service", "fallback"),
    )


@pytest.fixture
def context_factory(request):
    def _context_factory(forbidden_fields=None):
        ctx = Context()
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
