from df_engine.core.keywords import TRANSITIONS, RESPONSE
from df_engine.core import Context, Actor
import df_engine.conditions as cnd

from df_runner import ScriptRunner

script = {
    "greeting_flow": {
        "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},  # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: "Hi, how are you?",  # When the agent goes to node1, we return "Hi, how are you?"
            TRANSITIONS: {"node2": cnd.exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": cnd.exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")},
        },
        "node4": {RESPONSE: "bye", TRANSITIONS: {"node1": cnd.exact_match("Hi")}},
        "fallback_node": {  # We get to this node if an error occurred while the agent was running
            RESPONSE: "Ooops",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
    }
}


def get_some_intent(ctx: Context, actor: Actor):
    ctx.misc["some_detection"] = {ctx.last_request: "some_intent"}
    return ctx


def get_another_intent(ctx: Context, actor: Actor):
    ctx.misc["another_detection"] = {ctx.last_request: "another_intent"}
    return ctx


def print_misc(ctx: Context, actor: Actor):
    print(f"{ctx.misc=}")
    return ctx


runner = ScriptRunner(
    script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    pre_annotators=[get_some_intent, get_another_intent],
    post_annotators=[print_misc],
)


if __name__ == "__main__":
    runner.start()
