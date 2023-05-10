from dff.core.engine.core.actor import Actor
from dff.core.engine.core import keywords as kw

dictionary = {"node": {kw.RESPONSE: "hi"}}

script = {"flow": dictionary}

actor = Actor(
    script,
    ("flow", "node"),
)
