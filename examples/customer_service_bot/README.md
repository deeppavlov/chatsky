## Description

### Customer service bot

Customer service bot built using `DFF`. Uses Telegram as an interface.
This bot is designed to answer any type of user questions in a limited business domain (book shop).

* [DeepPavlov Intent Catcher](https://docs.deeppavlov.ai/en/0.14.1/features/models/intent_catcher.html) is used for intent retrieval.
* [ChatGPT](https://openai.com/pricing#language-models) is used for context based question answering.

### Intent Catcher

Intent catcher is a DistilBERT-based classifier for user intent classes.
We use the DeepPavlov library for a seamless training and inference experience.
Sample code for training the model can be found in `Training_intent_catcher.ipynb`.
The model is deployed as a separate microservice running at port 4999.

The bot interacts with the container via `/respond` endpoint.
The API expects a json object with the dialog history passed as an array and labeled 'dialog_contexts'. Intents will be extracted from the last utterance.

```json
{
    "dialog_contexts": ["phrase_1", "phrase_2"]
}
```

The API responds with a nested array containing `label - score` pairs.

```json
[["no",0.3393537402153015]]
```

Run the intent catcher:
```commandline
docker compose up --build --abort-on-container-exit --exit-code-from intent_client
```

## Running the bot

### Step 1: Configuring the docker services
To interact with external APIs, the bot requires API tokens that can be set through the [.env](.env) file. Update it replacing the placeholders with actual token values.
```
TG_BOT_TOKEN=***
OPENAI_API_TOKEN=***
```

### Step 2: Launching the project
*The commands below need to be run from the /examples/customer_service_bot directory*

Building the bot and launching it in the background can be done with a single command given that the environment variables have been configured correctly. Then you can immediately interact with your bot in Telegram.
```commandline
docker-compose up -d
```

If any of the source files have received updates, you can rebuild and sync the bot using the docker-compose build command.
```commandline
docker compose build
```
In case of bugs, you can test whether the bot correctly handles basic functionality using the following command:
```commandline
docker compose run assistant pytest test.py
```

The bot can also be run as a self-standing service, i.e. without the intent catcher for a less resource-demanding workflow:
```commandline
docker compose run assistant python run.py
```
