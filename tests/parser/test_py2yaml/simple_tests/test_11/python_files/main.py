from df_engine.core.actor import Actor
from df_engine.core import keywords as kw

dictionary = {"node": {kw.RESPONSE: "hi"}}

script = {"flow": dictionary}

actor = Actor(
    script,
    ("flow", "node"),
)
