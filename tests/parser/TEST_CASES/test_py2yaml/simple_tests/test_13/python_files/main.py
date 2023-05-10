from dff.core.engine.core.actor import Actor
from dff.core.engine.core import keywords as kw

strs = strings = {"node": "node"}

dicts = {1: {strs["node"]: {kw.RESPONSE: "hi"}}}

script = {"flow": dicts[1]}

actor = Actor(
    script,
    ("flow", strings["node"]),
)
