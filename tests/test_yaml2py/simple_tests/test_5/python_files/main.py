from df_engine.core.actor import Actor as Actor
from scripts import script as script

actor = Actor(script=script, start_label=("flow", "node"))
