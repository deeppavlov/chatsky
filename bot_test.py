from dff.script import conditions as cnd
from dff.script import RESPONSE, TRANSITIONS, Message, Context
from dff.pipeline import Pipeline

from dff.messengers.vk import PollingVKInterface
from tests.messengers.vk.vk_dummy import VKDummy



script = {
    "greeting_flow": {
        "start_node": { 
            RESPONSE: Message(),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))}
        },
        "node1": {
            RESPONSE: Message(
                text="Hi, how are you?"
            ),
            TRANSITIONS: {
                "start_node": cnd.exact_match(Message("Nice"))
            },
        },
        "fallback_node": {
            RESPONSE: Message(text="Sorry, I don't understand."),
            TRANSITIONS: {
                "start_node": cnd.true(),
            }
        }
    }
}


# KEY = "vk1.a.BvmniZCwChZfKGPWTUtHiFOC1GOQ7M7ePur6y9cs9YpKuKXLKQLDGZDy5fxhiJAFWXNLAKazSRjFqpw5WByX1x-KiEU3HcIb4QHSG_utQMjnqQ4UOYXcT7pn-8nUeo4hnf-nH4BIB3fdwq0WhZLTcnlLAok2sxd_yR2q8LVzElc-7rhZAuyNDcLzOxFx9Z9P3xsg5EEhDFBcWRvGk_1R1Q"
# GROUP_ID = "224377718"


vk_dummy = VKDummy()
vk_interface = PollingVKInterface("KEY", "GROUP_ID")
vk_interface.bot = vk_dummy

pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=vk_interface,
)
pipeline.run()
# vk_interface._respond(ctx)
print(vk_dummy.responses)

