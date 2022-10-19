from df_engine.core.actor import Actor
from df_engine.core import keywords

script = {"flow": {"node": {keywords.RESPONS: "hi"}}}

actor = Actor(
    script,
    ("flow", "node"),
)
