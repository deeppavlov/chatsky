from flows.start import flow
from dff.core.engine.core.actor import Actor


act = Actor(script={"start_flow": flow}, start_label=("start_flow", "start_node"))
