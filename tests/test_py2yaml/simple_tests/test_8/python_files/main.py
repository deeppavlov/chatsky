from df_engine.core.actor import Actor
from df_engine.core import keywords

ints = {1: 2}

strings = {1: {2: "flow"}}

script = {strings[1][ints[1]]: {"node": {keywords.RESPONSE: "hi"}}}

actor = Actor(
    script,
    (strings[1][ints[1]], "node"),
)
