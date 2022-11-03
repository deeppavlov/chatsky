from dff.core.engine.core.actor import Actor as act
from dff.core.engine.core.keywords import GLOBAL as glb
from dff.core.engine.core.keywords import RESPONSE as rsp
import python_files.flows as flows

script = {glb: {rsp: "glb"}, "start_flow": flows.sf, "fallback_flow": flows.ff}
actor = act(
    fallback_label=("fallback_flow", "fallback_node"),
    start_label=("start_flow", "start_node"),
    script=script,
)
