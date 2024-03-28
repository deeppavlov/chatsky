# %% [markdown]
"""
# VK: 2. Using Attachments

In this tutorial we will send messages with different types of attachments. When working with media and documents in VK you should keep in mind platform limitations on size and type of uploaded files. Here is the list of restrictions for each attachment type:

**Image:**
- Supported types: *JPG, PNG, GIF*
- Max file size: *50 Mb*
- Aspect ratio: *at least 1:20*

**Audio:**
- Supported types: *MP3*
- Max file size: *200 Mb*

**Video:**
- Supported types: *AVI, MP4, 3GP, MPEG, MOV, MP3, FLV, WMV*

**Documents:**
- Executable files are NOT supported (e.g. *.exe*, *.apk*)
- Max file size: *200 Mb*

**Consider checking latest version [VK documentation](https://dev.vk.com/en/api/upload/overview) for up-to-date file policies.**

So we advise you sending unsupported files as a link in a `text` field of a Message of via `Document` type attachment.
Here we'll create a simple script that will utilize sending images and files.

Import necessary modules:
"""

# %%
from dff.messengers.vk import PollingVKInterface
from dff.script import conditions as cnd
from dff.script import labels as lbl
from dff.script import RESPONSE, TRANSITIONS, Message
from dff.pipeline import Pipeline

from dff.script.core.message import Document, Image, Message


# %% [markdown]
"""
Sending images support both URL source and full local path
"""


# %%
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
            RESPONSE: Message(text="Here is your book!", attachments=[Document(source="book.pdf")]),
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

# %% [markdown]
"""
Here you put your `access_key` and `group_id` of the group your bot connected to.
"""

# %%
KEY = "<YOUR_ACCESS_KEY>"
GROUP_ID = "<YOUR_GROUP_ID>"

interface = PollingVKInterface(token=KEY, group_id=GROUP_ID, interval='2')

# %%

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

#%% [markdown]
"""
Knonw issue: when sending an Image with URL make sure it ends with `.png` or any other image extention, otherwise interface will fail fetching image bytes. Also some websites does not allow fetching images from them without registration, so it is more reliable to send data that is stored on your machine.
"""