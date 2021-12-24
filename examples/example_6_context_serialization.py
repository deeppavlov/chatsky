import logging

from df_engine.core.keywords import TRANSITIONS, RESPONSE
from df_engine.core import Context, Actor

from examples import example_1_basics
import df_engine.conditions as cnd

logging.basicConfig(
    format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def response_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return f"answer {len(ctx.requests)}"


# a dialog script
plot = {
    "flow_start": {"node_start": {RESPONSE: response_handler, TRANSITIONS: {("flow_start", "node_start"): cnd.true()}}}
}


actor = Actor(plot, start_label=("flow_start", "node_start"))


testing_dialog = [("hi", "answer 1"), ("how are you?", "answer 2"), ("ok", "answer 3"), ("good", "answer 4")]


def run_test():
    ctx = {}
    iterator = iter(testing_dialog)
    in_request, true_out_response = next(iterator)
    # pass as empty context
    _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)
    # serialize context to json str
    ctx = ctx.json()
    if isinstance(ctx, str):
        logging.info("context serialized to json str")
    else:
        raise Exception(f"ctx={ctx} has to be serialized to json string")
    in_request, true_out_response = next(iterator)
    _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)
    # serialize context to dict
    ctx = ctx.dict()
    if isinstance(ctx, dict):
        logging.info("context serialized to dict")
    else:
        raise Exception(f"ctx={ctx} has to be serialized to dict")
    in_request, true_out_response = next(iterator)
    _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)
    # context without serialization
    if not isinstance(ctx, Context):
        raise Exception(f"ctx={ctx} has to have Context type")
    in_request, true_out_response = next(iterator)
    _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


if __name__ == "__main__":
    # run_test()
    example_1_basics.run_interactive_mode(actor)
