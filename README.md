
# Dialog Flow Framework

The Dialog Flow Framework (DFF) allows you to write conversational services.
The service is written by defining a special dialog graph that describes the behavior of the dialog service.
The dialog graph contains the dialog script. DFF offers a specialized language (DSL) for quickly writing dialog graphs.
You can use it in services such as writing skills for Amazon Alexa, etc., chatbots for social networks, website call centers, etc.

[![Documentation Status](https://github.com/deeppavlov/dialog_flow_framework/workflows/build_and_publish_docs/badge.svg)](https://deeppavlov.github.io/dialog_flow_framework)
[![Codestyle](https://github.com/deeppavlov/dialog_flow_framework/workflows/codestyle/badge.svg)](https://github.com/deeppavlov/dialog_flow_framework/actions/workflows/codestyle.yml)
[![Tests](https://github.com/deeppavlov/dialog_flow_framework/workflows/test_coverage/badge.svg)](https://github.com/deeppavlov/dialog_flow_framework/actions/workflows/test_coverage.yml)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/deeppavlov/dialog_flow_framework/blob/master/LICENSE)
![Python 3.7, 3.8, 3.9](https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9-green.svg)
[![PyPI](https://img.shields.io/pypi/v/dff)](https://pypi.org/project/dff/)
[![Downloads](https://pepy.tech/badge/dff)](https://pepy.tech/project/dff)

# Quick Start
## Installation

DFF can be installed via pip:

```bash
pip install dff
```

The above command will set the minimum dependencies to start working with DFF. 
The installation process allows the user to choose from different packages based on their dependencies, which are:
```bash
pip install dff[core]  # minimal dependencies (by default)
pip install dff[redis]  # dependencies for using Redis
pip install dff[mongodb]  # dependencies for using MongoDB
pip install dff[mysql]  # dependencies for using MySQL
pip install dff[postgresql]  # dependencies for using PostgreSQL
pip install dff[sqlite]  # dependencies for using SQLite
pip install dff[ydb]  # dependencies for using Yandex Database
pip install dff[full]  # full dependencies including all options above
pip install dff[tests]  # dependencies for running tests
pip install dff[test_full]  # full dependencies for running all tests (all options above)
pip install dff[examples]  # dependencies for running examples (all options above)
pip install dff[devel]  # dependencies for development
pip install dff[doc]  # dependencies for documentation
pip install dff[devel_full]  # full dependencies for development (all options above)
```

For example, if you are going to use one of the database backends,
you can specify the corresponding requirements yourself. Multiple dependencies can be installed at once, e.g.
```bash
pip install dff[postgresql, mysql]
```

## Basic example

```python
from dff.script import GLOBAL, TRANSITIONS, RESPONSE, Context, Actor, Message
import dff.script.conditions.std_conditions as cnd
from typing import Union

# create a dialog script
script = {
    GLOBAL: {
        TRANSITIONS: {
            ("flow", "node_hi"): cnd.exact_match(Message(text="Hi")),
            ("flow", "node_ok"): cnd.true()
        }
    },
    "flow": {
        "node_hi": {RESPONSE: Message(text="Hi!!!")},
        "node_ok": {RESPONSE: Message(text="Okey")},
    },
}

# init actor
actor = Actor(script, start_label=("flow", "node_hi"))


# handler requests
def turn_handler(in_request: Message, ctx: Union[Context, dict], actor: Actor):
    # Context.cast - gets an object type of [Context, str, dict] returns an object type of Context
    ctx = Context.cast(ctx)
    # Add in current context a next request of user
    ctx.add_request(in_request)
    # Pass the context into actor and it returns updated context with actor response
    ctx = actor(ctx)
    # Get last actor response from the context
    out_response = ctx.last_response
    # The next condition branching needs for testing
    return out_response, ctx


ctx = {}
while True:
    in_request = input("type your answer: ")
    out_response, ctx = turn_handler(Message(text=in_request), ctx, actor)
    print(out_response.text)
```

When you run this code, you get similar output:
```
type your answer: hi
Okey
type your answer: Hi
Hi!!!
type your answer: ok
Okey
type your answer: ok
Okey
```

To get more advanced examples, take a look at
[examples](https://github.com/deeppavlov/dialog_flow_framework/tree/dev/examples) on GitHub.

# Context Storages
## Description

Context Storages allow you to save and retrieve user dialogue states
(in the form of a `Context` object) using various database backends. 

The following backends are currently supported:
* [JSON](https://www.json.org/json-en.html)
* [pickle](https://docs.python.org/3/library/pickle.html)
* [shelve](https://docs.python.org/3/library/shelve.html)
* [SQLite](https://www.sqlite.org/index.html)
* [PostgreSQL](https://www.postgresql.org/)
* [MySQL](https://www.mysql.com/)
* [MongoDB](https://www.mongodb.com/)
* [Redis](https://redis.io/)
* [Yandex DataBase](https://ydb.tech/)

Aside from this, we offer some interfaces for saving data to your local file system.
These are not meant to be used in production, but can be helpful for prototyping your application.

## Basic example

```python
from dff.script import Context, Actor
from dff.context_storages import SQLContextStorage
from .script import some_df_script

db = SQLContextStorage("postgresql+asyncpg://user:password@host:port/dbname")

actor = Actor(some_df_script, start_label=("root", "start"), fallback_label=("root", "fallback"))


def handle_request(request):
    user_id = request.args["user_id"]
    if user_id not in db:
        context = Context(id=user_id)
    else:
        context = db[user_id]
    new_context = actor(context)
    db[user_id] = new_context
    assert user_id in db
    return new_context.last_response

```

To get more advanced examples, take a look at
[examples](https://github.com/deeppavlov/dialog_flow_framework/tree/dev/examples/context_storages) on GitHub.

# Quick Start -- extended_conditions
## Description

Dialog Flow Extended Conditions allow for integration of various machine learning models for Natural Language Understanding (NLU) into DFF scripting. The former include the language modelling tools provided by `Sklearn`, `Gensim`, and `HuggingFace` as well as cloud-hosted services (`Rasa NLU`, `Google Dialogflow`). 

## Installation
```bash
pip install dff[async] # required by RASA and HuggingFace iference API
pip install dff[dialogflow]
pip install dff[sklearn]
pip install dff[gensim]
pip install dff[huggingface] # for local deployment of hf models
```
## Instantiate a model

The library provides a number of wrappers for different model types. All these classes implement a uniform interface.

 - `namespace_key` should be used in all types of models to save the annotation results to separate namespaces in the context. 
 - The `model` parameter is set either with the local model instance or with the address of an external annotator.

However, some of the parameters are class-specific.

 - The `tokenizer` parameter is only required for Sklearn, Gensim, and HuggingFace models. See the signature of the corresponding classes for more information.
 - `device` parameter is only required for Hugging Face models. Use torch.device("cpu") or torch.device("cuda").
 - `dataset` should be passed to all cosine matchers, so that they have a pre-defined set of labels and examples, against which user utterances will be compared.

Using the library, you can deploy models locally.

```python
hf_model = HFClassifier(
    model=model,
    tokenizer=tokenizer,
    device=torch.device("cpu")
    namespace_key="HF"
)
```

Another option is to employ remotely hosted annotators. For instance, you can connect to a running RASA service for NLU annotations.

```python
rasa_model = RasaModel(
    model="http://my-rasa-server",
    namespace_key="rasa",
)
```

## Use the Model class in your Script graph

Annotation should be performed at the `PRE_TRANSITION_PROCESSING` step.

```python
script = {
    GLOBAL: {
        PRE_TRANSITION_PROCESSING: {
            "get_intents_from_rasa": rasa_model 
        }
    }
}
```

Extracted values can be accessed by all functions that use the `Context` object.
We provide several such functions that can be leveraged as transition conditions.

```python
from df_extended_conditions.conditions import has_cls_label

script = {
    "root": {
        "start": {
            TRANSITIONS: {
                ("next_flow", "next_node"): has_cls_label("user_happy", threshold=0.9, namespace="some_model")
            }
        }
    },
    ...
}
```

To get more advanced examples, take a look at [examples](https://github.com/deeppavlov/dialog_flow_framework/tree/dev/examples) on GitHub.

# Contributing to the Dialog Flow Framework

Please refer to [CONTRIBUTING.md](https://github.com/deeppavlov/dialog_flow_framework/blob/dev/CONTRIBUTING.md).