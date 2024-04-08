# %%
from dff.pipeline import Pipeline
from dff.script import Context
from dff.script.responses import random_choice


def test_response():
    ctx = Context()
    pipeline = Pipeline.from_script(script={"flow": {"node": {}}}, start_label=("flow", "node"))
    for _ in range(10):
        assert random_choice(["text1", "text2"])(ctx, pipeline) in ["text1", "text2"]
