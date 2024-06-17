# %% [markdown]
"""
# VK: 1. Basic

The following tutorial shows how to run a regular DFF script as a VK Bot.

Before we start, we will need to setup our bot in VK, what can be done through these steps:
1. Create a community in VK.
![photo_1](https://imgur.com/NaCfts6.png)

2. Follow this [guide](https://dev.vk.com/en/api/bots/getting-started) to obtain an access token.
NOTE: Current version of DFF VK Interface only works with [Bots Long Poll API](https://dev.vk.com/en/api/bots-long-poll/getting-started)

3. Grant access to required scopes for your bot.
![photo_2](https://imgur.com/or5NUxy.png)

4. Make sure to enable Long Poll API and set up events your bot will listen to.
![photo_3](https://imgur.com/or5NUxy.png)
![photo_4](https://imgur.com/kJtXTnV.png)

"""

# %%
from dff.messengers.vk import PollingVKInterface
from dff.script import conditions as cnd
from dff.script import labels as lbl
from dff.script import RESPONSE, TRANSITIONS, Message
from dff.pipeline import Pipeline

from dff.script.core.message import Image, Message


# %% [markdown]
"""
Then you can specify your script as usual.
More extensive guide on working with attachments with examples and best practices. (link)
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
            RESPONSE: Message(text="Hi"),
            TRANSITIONS: {lbl.repeat(): cnd.true()},
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
You can check id of your group via many web services, for example https://regvk.com/id/.
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
