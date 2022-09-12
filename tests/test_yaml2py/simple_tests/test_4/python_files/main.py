from df_engine.core.actor import Actor as Actor
from df_engine.core import keywords as kw

another_script = {"flow": {"node": {kw.RESPONSE: "hi"}}}
script = another_script
actor = Actor(script=script, start_label=("flow", "node"))
