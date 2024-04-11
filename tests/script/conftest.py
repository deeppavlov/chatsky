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
def ctx():
    return Context()
