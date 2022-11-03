from dff.core.engine.core.actor import Actor as Actor
from dff.core.engine.core import keywords as keywords

script = {keywords.GLOBAL: {keywords.RESPONSE: ""}}
actor = Actor(script=script, start_label=(keywords.GLOBAL, keywords.RESPONSE))
