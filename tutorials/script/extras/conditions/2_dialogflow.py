# %% [markdown]
"""
# 2. Dialogflow

The tutorial below demonstrates, how to integrate Google Dialogflow into your script logic using `llm_conditions`.
The way of using the `GoogleDialogFlowModel` class is similar to that of other models.
Tutorials for other models can be found in the same section.
"""

# %pip install dff[ext,dialogflow]

# %%
import logging

logging.basicConfig(level=logging.INFO)

from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
    GLOBAL,
    Message,
)
from chatsky.ml.models.google_dialogflow_model import (
    GoogleDialogFlowModel,
)
from chatsky.conditions.ml import HasLabel
from chatsky.messengers.console import CLIMessengerInterface


# %% [markdown]
"""
All you need to instantiate the `GoogleDialogFlowModel` class are
Google API credentials. You can obtain further instructions
on how to get those in the class documenation.

After you have received the credentials in the form of a json file,
you can use them to construct the class.
"""


# %%
gdf_model = GoogleDialogFlowModel.from_file(filename="acc_data.json")

# %%
script = {
    GLOBAL: {
        # Intents from Google Dialogflow can be used in conditions to traverse your dialog graph
        TRANSITIONS: [
            Tr(
                cnd=HasLabel(
                    label="Default Welcome Intent", model_name="gdf_model"
                ),
                dst=("root", "finish"),
                priority=1.2,
            )
        ],
    },
    "root": {
        "start": {
            RESPONSE: Message(text="Hi!"),
            TRANSITIONS: [Tr(cnd=True, dst="fallback")],
        },
        "fallback": {
            RESPONSE: Message(text="I can't quite get what you mean.")
        },
        "finish": {RESPONSE: Message(text="Ok, see you soon!")},
    },
}


# %%
pipeline = Pipeline(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting Dff bot..."),
    models={"gdf_model": gdf_model},
)


# %%
if __name__ == "__main__":
    pipeline.run()
