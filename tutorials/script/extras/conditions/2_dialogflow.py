# %% [markdown]
"""
# Google Dialogflow Integration Tutorial

This tutorial demonstrates how to integrate Google Dialogflow with Chatsky to
create more sophisticated
dialog management systems. We'll show how to:

1. Set up Dialogflow integration
2. Create a basic bot that understands intents
3. Handle different user intents with appropriate responses
4. Structure a multi-turn conversation

## Prerequisites

- A Google Cloud account with Dialogflow enabled
- Dialogflow API credentials (JSON file)
- Basic understanding of Chatsky's Pipeline and transitions

First, install the required dependencies:
"""

# %%
# %pip install chatsky google-cloud-dialogflow

# %%
from typing import Dict, Any

from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
    GLOBAL,
    Message,
)
from chatsky.ml.models.google_dialogflow_model import GoogleDialogFlowModel
from chatsky.conditions.ml import HasLabel
from chatsky.messengers.console import CLIMessengerInterface

# %% [markdown]
"""
## Setting Up Dialogflow

Before using Dialogflow with Chatsky, you'll need to:

1. Create a project in Google Cloud Console
2. Enable Dialogflow API
3. Create a service account and download credentials (JSON file)
4. Set up intents in Dialogflow console

For detailed setup instructions, visit the
[Dialogflow documentation](https://cloud.google.com/dialogflow/docs).

Let's initialize our Dialogflow model:
"""

# %%
# Initialize Dialogflow model with credentials
gdf_model = GoogleDialogFlowModel.from_file(filename="gdf_account.json")

# %% [markdown]
"""
## Creating an Enhanced Dialog Script

We'll create a more sophisticated script that handles multiple intents:
- Greeting intents
- Help requests
- Goodbye intents
- Fallback for unrecognized inputs
"""

# %%
script: Dict[str, Any] = {
    GLOBAL: {
        TRANSITIONS: [
            # Handle welcome intents globally
            Tr(
                cnd=HasLabel(
                    label="Default Welcome Intent", pipeline_model="gdf_model"
                ),
                dst=("root", "welcome"),
                priority=1.2,
            ),
            # Handle goodbye intents
            Tr(
                cnd=HasLabel(
                    label="Default Goodbye Intent", pipeline_model="gdf_model"
                ),
                dst=("root", "goodbye"),
                priority=1.1,
            ),
            # Handle help requests
            Tr(
                cnd=HasLabel(label="Help Intent", pipeline_model="gdf_model"),
                dst=("root", "help"),
                priority=1.0,
            ),
        ],
    },
    "root": {
        "start": {
            RESPONSE: Message(text="Hello! How can I help you today?"),
            TRANSITIONS: [Tr(cnd=True, dst="waiting_input")],
        },
        "welcome": {
            RESPONSE: Message(
                text="Welcome! I'm your assistant. Feel free to ask questions!"
            ),
            TRANSITIONS: [Tr(cnd=True, dst="waiting_input")],
        },
        "waiting_input": {
            RESPONSE: Message(text="I'm listening..."),
            TRANSITIONS: [Tr(cnd=True, dst="fallback")],
        },
        "help": {
            RESPONSE: Message(
                text="I can help you with various tasks. Try asking me about:\n"
                "- General information\n"
                "- Getting started\n"
                "- Common problems"
            ),
            TRANSITIONS: [Tr(cnd=True, dst="waiting_input")],
        },
        "fallback": {
            RESPONSE: Message(
                text="I'm not sure I understand. "
                "Could you rephrase that or ask for help?"
            ),
            TRANSITIONS: [Tr(cnd=True, dst="waiting_input")],
        },
        "goodbye": {
            RESPONSE: Message(text="Goodbye! Have a great day!"),
        },
    },
}

# %% [markdown]
"""
## Creating and Running the Pipeline

Now we'll set up our pipeline with the enhanced script and run it:
"""

# %%
# Initialize the pipeline with our script and Dialogflow model
pipeline = Pipeline(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(
        intro="Starting Dialogflow bot..."
    ),
    models={"gdf_model": gdf_model},
)

# %%
if __name__ == "__main__":
    pipeline.run()
