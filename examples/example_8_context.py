import logging

from dff.core.keywords import GLOBAL, TRANSITIONS, RESPONSE
from dff.core import Context, Actor
import dff.labels as lbl

logging.basicConfig(
    format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# custom functions
def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


def response(ctx: Context, actor: Actor, *args, **kwargs) -> str:
    request_len = len(ctx.last_request)
    ctx.misc["lens"] = ctx.misc.get("lens", []) + [request_len]
    return ctx.misc.get("prompt", "") + f"{request_len}"


# a dialog script
plot = {
    GLOBAL: {TRANSITIONS: {trn.repeat(): always_true}},
    "start": {
        "start": {
            RESPONSE: response,
        },
    },
}


ctx = Context()
actor = Actor(plot, start_label=("start", "start"))
ctx.misc["prompt"] = "Lenght of request "
while True:
    in_text = input("you: ")
    ctx.add_request(in_text)
    ctx = actor(ctx)
    print(f"{ctx.misc=}")
    print(f"bot: {ctx.last_response}")
