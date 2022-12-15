# %%
from dff.script import Context, Actor
from dff.script.responses import choice


def test_response():
    ctx = Context()
    actor = Actor(script={"flow": {"node": {}}}, start_label=("flow", "node"))
    for _ in range(10):
        assert choice(["text1", "text2"])(ctx, actor) in ["text1", "text2"]
