import pytest

from chatsky.script import Message, TRANSITIONS, RESPONSE, Context
from chatsky.script import conditions as cnd
from chatsky.pipeline import Pipeline
from chatsky.slots.slots import SlotNotExtracted


@pytest.fixture(scope="function", autouse=True)
def patch_exception_equality(monkeypatch):
    monkeypatch.setattr(
        SlotNotExtracted, "__eq__", lambda self, other: type(self) is type(other) and self.args == other.args
    )
    yield


@pytest.fixture(scope="function")
def pipeline():
    script = {"flow": {"node": {RESPONSE: Message(), TRANSITIONS: {"node": cnd.true()}}}}
    pipeline = Pipeline(script=script, start_label=("flow", "node"))
    return pipeline


@pytest.fixture(scope="function")
def context():
    ctx = Context()
    ctx.add_request(Message(text="Hi"))
    return ctx
