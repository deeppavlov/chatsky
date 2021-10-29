from dff.core.keywords import GLOBAL, TRANSITIONS, RESPONSE
from dff.core import Context, Actor
import dff.conditions as cnd
from typing import Union

# create plot of dialog
plot = {
    GLOBAL: {TRANSITIONS: {("flow", "node_hi"): cnd.exact_match("Hi"), ("flow", "node_ok"): cnd.true()}},
    "flow": {
        "node_hi": {RESPONSE: "Hi!!!"},
        "node_ok": {RESPONSE: "Okey"},
    },
}

# init actor
actor = Actor(plot, start_label=("flow", "node_hi"))


# handler requests
def turn_handler(in_request: str, ctx: Union[Context, dict], actor: Actor):
    # Context.cast - gets an object type of [Context, str, dict] returns an object type of Context
    ctx = Context.cast(ctx)
    # Add in current context a next request of user
    ctx.add_request(in_request)
    # pass the context into actor and it returns updated context with actor response
    ctx = actor(ctx)
    # get last actor response from the context
    out_response = ctx.last_response
    # the next condition branching needs for testing
    return out_response, ctx


ctx = {}
while True:
    in_request = input("type your answer: ")
    out_response, ctx = turn_handler(in_request, ctx, actor)
    print(out_response)
