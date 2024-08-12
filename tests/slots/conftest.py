import pytest

from chatsky.core import Message, TRANSITIONS, RESPONSE, Context, Pipeline, Transition as Tr
from chatsky import conditions as cnd
from chatsky.slots.slots import SlotNotExtracted


@pytest.fixture(scope="function", autouse=True)
def patch_exception_equality(monkeypatch):
    monkeypatch.setattr(
        SlotNotExtracted, "__eq__", lambda self, other: type(self) is type(other) and self.args == other.args
    )
    yield


@pytest.fixture(scope="function")
def pipeline():
    script = {"flow": {"node": {RESPONSE: Message(), TRANSITIONS: [Tr(dst="node")]}}}
    pipeline = Pipeline.from_script(script=script, start_label=("flow", "node"))
    return pipeline


@pytest.fixture(scope="function")
def context(pipeline):
    ctx = Context()
    ctx.add_request(Message(text="Hi"))
    ctx.framework_data.pipeline = pipeline
    return ctx
