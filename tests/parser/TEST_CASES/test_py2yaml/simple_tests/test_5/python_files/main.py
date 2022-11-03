from dff.core.engine.core.actor import Actor
from dff.core.engine.core import keywords

script = {keywords.GLOBAL: {"keywords.RESPONSE": ""}}

actor = Actor(
    script,
    (keywords.GLOBAL, "keywords.RESPONSE"),
)
