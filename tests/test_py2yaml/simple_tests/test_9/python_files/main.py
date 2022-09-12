from df_engine.core.actor import Actor
from df_engine.core import keywords as kw

another_script = script = {"flow": {"node": {kw.RESPONSE: "hi"}}}

actor = Actor(
    script,
    ("flow", "node"),
)
