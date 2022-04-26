# %%
from df_engine.core import Context, Actor
import df_engine.responses as rsp


def test_response():
    ctx = Context()
    actor = Actor(script={"flow": {"node": {}}}, start_label=("flow", "node"))
    for _ in range(10):
        assert rsp.choice(["text1", "text2"])(ctx, actor) in ["text1", "text2"]
