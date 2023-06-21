import pytest

from dff.script import Context, Message, TRANSITIONS, RESPONSE
from dff.script import conditions as cnd
from dff.pipeline import Pipeline
from dff.script.logic.slots.root import root_slot


@pytest.fixture
def testing_pipeline():
    script = {"old_flow": {"": {RESPONSE: lambda c, p: Message(), TRANSITIONS: {"": cnd.true()}}}}
    pipeline = Pipeline.from_script(script=script, start_label=("old_flow", ""))
    yield pipeline


@pytest.fixture
def testing_context():
    ctx = Context()
    ctx.add_request("I am Groot")
    yield ctx


@pytest.fixture(scope="session")
def root():
    yield root_slot
