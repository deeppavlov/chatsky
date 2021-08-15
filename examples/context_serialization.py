import logging
import json

from dff.core.keywords import TRANSITIONS, GRAPH, RESPONSE
from dff.core import Context, Actor

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# custom functions
def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


# a dialog script
flows = {
    "flow_start": {
        GRAPH: {
            "node_start": {
                RESPONSE: "yep",
                TRANSITIONS: {
                    ("flow_start", "node_start"): always_true,
                },
            }
        },
    },
}


actor = Actor(flows, start_node_label=("flow_start", "node_start"))
request_json = "{}"
# Start
for _ in range(10):
    print(f"incomming data={request_json}")
    # deserialization
    data_dict = json.loads(request_json)
    ctx = Context.parse_obj(data_dict) if data_dict else Context()
    # or you can use ctx = Context.parse_raw(request_json)

    in_text = "yep"
    print(f"you: {in_text}")
    ctx.add_human_utterance(in_text)
    ctx = actor(ctx)
    print(f"bot: {ctx.actor_text_response}")

    # serialization
    request_json = ctx.json()
    # if you want to get serializable obj jusc use `data_dict = json.loads(ctx.json())`
