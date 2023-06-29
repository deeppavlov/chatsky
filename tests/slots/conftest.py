from uuid import uuid4
import pytest

from dff.script import Message, TRANSITIONS, RESPONSE
from dff.script import conditions as cnd
from dff.pipeline import Pipeline
from dff.script.slots import root_slot


@pytest.fixture
def testing_pipeline():
    script = {"old_flow": {"": {RESPONSE: lambda c, p: Message(), TRANSITIONS: {"": cnd.true()}}}}
    pipeline = Pipeline.from_script(script=script, start_label=("old_flow", ""))
    yield pipeline


@pytest.fixture
def testing_context(testing_pipeline: Pipeline):
    ctx_id = uuid4()
    ctx = testing_pipeline(Message(text="Hi!"), ctx_id)
    yield ctx


@pytest.fixture(scope="session")
def root():
    yield root_slot
