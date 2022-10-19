from flows.start import flow as flow
from dff.core.engine.core.actor import Actor as Actor

act = Actor(script={"start_flow": flow}, start_label=("start_flow", "start_node"))
