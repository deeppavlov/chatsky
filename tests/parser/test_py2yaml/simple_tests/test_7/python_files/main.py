from dff.core.engine.core.actor import Actor
from dff.core.engine.core import keywords

script = {"flow": {"node": {keywords.RESPONS: "hi"}}}

actor = Actor(
    script,
    ("flow", "node"),
)
