# %% [markdown]
"""
# Core: 10. Multiple fallback nodes

This tutorial shows basics of creating a separate fallback node for every flow. In this case it is done via `LOCAL` nodes.

Let's do all the necessary imports from DFF:
"""

# %pip install dff


"""Importing all the necessary modules:"""

# %%
from dff.pipeline import Pipeline
from dff.script import TRANSITIONS, RESPONSE, Message, LOCAL
import dff.script.conditions as cnd

# %% [markdown]
"""
Let's create a script that will consist of several flows, that can be accessed through dialogue:
"""

# %%
toy_script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(),
            TRANSITIONS: {
                ("greeting_flow", "say_hi_node"): cnd.true()
            }
        },

        "say_hi_node": {
            RESPONSE: Message(text="Hello, how can I help you?"),
            TRANSITIONS: {
                ("authorization_flow", "response_node"): cnd.exact_match(Message(text="/auth")),
                ("information_flow", "response_node"): cnd.exact_match(Message(text="/info"))
            }
        },

        "fallback_node": {
            RESPONSE: Message(text="Unknown Command. Try again."),
            TRANSITIONS: {"say_hi_node": cnd.exact_match(Message(text="hi"))
            }
        }
    },
    "authorization_flow": {
        LOCAL: {
            TRANSITIONS: {
                ("auth_fallback_node", 0.1):
                    cnd.true()
            }
        },
        "response_node": {
            RESPONSE: Message(text="Write your name, please."),
            TRANSITIONS: {
                ("authorization_flow", "auth_password_node"):
                    cnd.exact_match(Message(text="admin")),
                ("authorization_flow", "auth_success_node"):
                    cnd.exact_match(Message(text="John Doe"))
            }
        },

        "auth_success_node": {
            RESPONSE: Message(text="Authentication successful."),
            TRANSITIONS: {
                ("greeting_flow", "start_node"):
                    cnd.true()
            }
        },

        "auth_password_node": {
            RESPONSE: Message(text="Password required. Enter your password."),
            TRANSITIONS: {
                ("authorization_flow", "auth_success_node"):
                    cnd.exact_match(Message(text="123"))
            }
        },

        "auth_fallback_node": {
            RESPONSE: Message(text="User is not found or password is incorrect."),
            TRANSITIONS: {
                ("greeting_flow", "say_hi_node"):
                    cnd.true()
            }
        }
    },

    "information_flow": {
        LOCAL: {
            TRANSITIONS: {
                ("information_fallback_node", 0.1):
                    cnd.true()
            }
        },
        "response_node": {
            RESPONSE: Message(text="What information you would like to know?"),
            TRANSITIONS: {
                ("information_flow", "weather_city_node"):
                    cnd.exact_match(Message(text="weather")),
                ("information_flow", "time_node"):
                    cnd.exact_match(Message(text="time"))
            }
        },
        "weather_city_node": {
            RESPONSE: Message(text="What city are interested in?"),
            TRANSITIONS: {
                ("information_flow", "weather_moscow_node"):
                    cnd.exact_match(Message(text="Moscow")),
                ("information_flow", "weather_new_york_node"):
                    cnd.exact_match(Message(text="New York"))
            }
        },
        "weather_moscow_node": {
            RESPONSE: Message(text="It's -5 Celsius"),
            TRANSITIONS: {
                ("greeting_flow", "start_node"): cnd.true()
                }
        },
        "weather_new_york_node": {
            RESPONSE: Message(text="It's +14 Celsius"),
            TRANSITIONS: {
                ("greeting_flow", "start_node"): cnd.true()
                }
        },
        "time_node": {
            RESPONSE: Message(text="It's tea time!"),
            TRANSITIONS: {
                ("greeting_flow", "start_node"):
                    cnd.true()
            }
        },
        "information_fallback_node": {
            RESPONSE: Message(text="I don't know that information!"),
            TRANSITIONS: {
                ("information_flow", "response_node"):
                    cnd.true()
            }
        }
    }
}

# %% [markdown]
"""
As you can see, we've created specific fallback node for each individual flow using `LOCAL` node. Due to the low priority (explicitly set as `0.1`) this condition will trigger automatically if no other condition in any node in the flow was triggered.
Also we defined `fallback_label` in our `Pipeline` which is being overwritten with `LOCAL` nodes in flows they defined in.

And now let's run our script:
"""
# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node")
    )

if __name__ == "__main__":
    pipeline.run()
