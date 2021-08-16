import logging

from dff.core.keywords import GLOBAL_TRANSITIONS, GRAPH, RESPONSE
from dff.core import Context, Actor
from dff.transitions import repeat

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# custom functions
def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


def response(ctx: Context, actor: Actor, *args, **kwargs) -> str:
    request_len = len(ctx.last_request)
    ctx.misc["lens"] = ctx.misc.get("lens", []) + [request_len]
    return ctx.misc.get("prompt", "") + f"{request_len}"


# a dialog script
flows = {
    "start": {
        GLOBAL_TRANSITIONS: {repeat(): always_true},
        GRAPH: {
            "start": {
                RESPONSE: response,
            },
        },
    },
}


ctx = Context()
actor = Actor(flows, start_node_label=("start", "start"))
ctx.misc["prompt"] = "Lenght of request "
while True:
    in_text = input("you: ")
    ctx.add_request(in_text)
    ctx = actor(ctx)
    print(f"{ctx.misc=}")
    print(f"bot: {ctx.last_response}")
