from df_engine.core.actor import Actor
from df_engine.core import keywords

script = {keywords.GLOBAL: {keywords.RESPONSE: ""}}

actor = Actor(
    script,
    (keywords.GLOBAL, "keywords.RESPONSE"),
)
