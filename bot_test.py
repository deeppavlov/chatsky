from dff.messengers.vk import PollingVKInterface
from dff.script import conditions as cnd
from dff.script import labels as lbl
from dff.script import RESPONSE, TRANSITIONS, Message
from dff.pipeline import Pipeline

from dff.script.core.message import Image, Message, Document


script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: {
                "greeting_node": cnd.exact_match(Message(text="Hello"))
            },
        },
        "greeting_node": {
            RESPONSE: Message(text="Hello! What would you like to get?"),
            TRANSITIONS: {
                "cat_image_node": cnd.exact_match(Message(text="cat")),
                "book_file_node": cnd.exact_match(Message(text="book"))
            },
        },
        "cat_image_node": {
            RESPONSE: Message(text="Two cool cats sent.", attachments=[Image(source="https://media.tenor.com/ff2BZlCK0SwAAAAM/gatin.gif"), Image(source="https://d2ph5fj80uercy.cloudfront.net/04/cat2634.jpg")]),
            TRANSITIONS: {
                "greeting_node": cnd.true()
            }
        },
        "book_file_node": {
            RESPONSE: Message(text="Here is your book!", attachments=[Document(source="/home/askatasuna/Documents/DeepPavlov/DFF/dialog_flow_framework/LICENSE")]),
            TRANSITIONS: {
                "greeting_node": cnd.true()
            }
        },
        "fallback_node": {
            RESPONSE: Message(text="Please, repeat the request"),
            TRANSITIONS: {
                "greeting_node": cnd.exact_match(Message(text="/start"))
            },
        },
    }
}


KEY = "vk1.a.BvmniZCwChZfKGPWTUtHiFOC1GOQ7M7ePur6y9cs9YpKuKXLKQLDGZDy5fxhiJAFWXNLAKazSRjFqpw5WByX1x-KiEU3HcIb4QHSG_utQMjnqQ4UOYXcT7pn-8nUeo4hnf-nH4BIB3fdwq0WhZLTcnlLAok2sxd_yR2q8LVzElc-7rhZAuyNDcLzOxFx9Z9P3xsg5EEhDFBcWRvGk_1R1Q"
GROUP_ID = "224377718"

interface = PollingVKInterface(token=KEY, group_id=GROUP_ID)


pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,
    # The interface can be passed as a pipeline argument.
)

def main():
    pipeline.run()


if __name__ == "__main__":
    main()
