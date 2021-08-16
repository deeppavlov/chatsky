import logging
import json

from dff.core.keywords import TRANSITIONS, GRAPH, RESPONSE
from dff.core import Context, Actor

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# custom functions
def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


def response_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return f"answer {len(ctx.human_utterances)}"


# a dialog script
flows = {
    "flow_start": {
        GRAPH: {
            "node_start": {
                RESPONSE: response_handler,
                TRANSITIONS: {
                    ("flow_start", "node_start"): always_true,
                },
            }
        },
    },
}

actor = Actor(flows, start_node_label=("flow_start", "node_start"))


# def turn_handler(in_text, ctx=None):
#     if
#     request_json = "{}"
#     # Start
#     for _ in range(10):
#         print(f"incomming data={request_json}")
#         # deserialization
#         data_dict = json.loads(request_json)
#         ctx = Context.parse_obj(data_dict) if data_dict else Context()
#         # or you can use ctx = Context.parse_raw(request_json)

#         in_text = "yep"
#         print(f"you: {in_text}")
#         ctx.add_human_utterance(in_text)
#         ctx = actor(ctx)
#         print(f"bot: {ctx.actor_text_response}")

#         # serialization
#         request_json = ctx.json()
#         # if you want to get serializable obj jusc use `data_dict = json.loads(ctx.json())`


def turn_handler(in_request, ctx={}, true_out_response=None):
    ctx = Context.cast(ctx)
    ctx.add_human_utterance(in_request)
    ctx = actor(ctx)
    out_response = ctx.actor_text_response
    # Below
    if true_out_response is not None and true_out_response != out_response:
        logging.error(f"{in_request=} -> true_out_response != out_response: {true_out_response} != {out_response}")
    else:
        logging.info(f"{in_request=} -> {out_response}")
    return out_response, ctx


in_requests = ["hi", "how are you?", "ok", "good"]
out_responses = ["answer 1", "answer 2", "answer 3", "answer 4"]


def run_test():
    ctx = {}
    iterator = zip(in_requests, out_responses)
    in_request, true_out_response = next(iterator)
    # pass as empty context
    _, ctx = turn_handler(in_request, ctx={}, true_out_response=true_out_response)
    # pass as context json string
    ctx = ctx.json()
    if isinstance(ctx, str):
        logging.info("context serialize to json str")
    else:
        logging.error(f"{ctx=} has to be serializeed to json string")
    in_request, true_out_response = next(iterator)
    _, ctx = turn_handler(in_request, ctx=ctx, true_out_response=true_out_response)


if __name__ == "__main__":
    run_test()
