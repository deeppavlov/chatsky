from dff.core.engine.core.actor import Actor as Actor
from dff.core.engine.core import keywords as keywords

ints = {1: 2}
strings = {1: {2: "flow"}}
script = {strings[1][ints[1]]: {"node": {keywords.RESPONSE: "hi"}}}
actor = Actor(script=script, start_label=(strings[1][ints[1]], "node"))
