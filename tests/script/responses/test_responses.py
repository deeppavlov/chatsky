# %%
from chatsky.pipeline import Pipeline
from chatsky.script import Context
from chatsky.script.responses import choice


def test_response():
    ctx = Context()
    pipeline = Pipeline(script={"flow": {"node": {}}}, start_label=("flow", "node"))
    for _ in range(10):
        assert choice(["text1", "text2"])(ctx, pipeline) in ["text1", "text2"]
