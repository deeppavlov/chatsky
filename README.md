
# Dialog Flow Framework

The Dialog Flow Framework (DFF) allows you to write conversational services. The service is written by defining a special dialog graph that describes the behavior of the dialog service. The dialog graph contains the dialog script. DFF offers a specialized language (DSL) for quickly writing dialog graphs. You can use it in such services for writing skills for Amazon Alexa and etc, chat-bots for social networks, websites call-centers and etc. 

[![Documentation Status](https://readthedocs.org/projects/dialog-flow-engine/badge/?version=latest)](https://readthedocs.org/projects/dialog-flow-engine/badge/?version=latest)
[![Codestyle](https://github.com/deeppavlov/dialog_flow_framework/workflows/codestyle/badge.svg)](https://github.com/deeppavlov/dialog_flow_framework/actions)
[![Tests](https://github.com/deeppavlov/dialog_flow_framework/workflows/test_coverage/badge.svg)](https://github.com/deeppavlov/dialog_flow_framework/actions)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/deeppavlov/dialog_flow_framework/blob/master/LICENSE)
![Python 3.7, 3.8, 3.9](https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9-green.svg)
[![PyPI](https://img.shields.io/pypi/v/dff)](https://pypi.org/project/dff/)
[![Downloads](https://pepy.tech/badge/dff)](https://pepy.tech/project/dff)

# Quick Start -- dff
## Installation
```bash
pip install dff
```

## Basic example

```python
from dff.script import GLOBAL, TRANSITIONS, RESPONSE, Context, Actor, Message
import dff.script.conditions.std_conditions as cnd
from typing import Union

# create script of dialog
script = {
    GLOBAL: {TRANSITIONS: {("flow", "node_hi"): cnd.exact_match(Message(text="Hi")), ("flow", "node_ok"): cnd.true()}},
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
    # pass the context into actor and it returns updated context with actor response
    ctx = actor(ctx)
    # get last actor response from the context
    out_response = ctx.last_response
    # the next condition branching needs for testing
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

To get more advanced examples, take a look at [examples](https://github.com/deeppavlov/dialog_flow_framework/tree/dev/examples) on GitHub.

# Quick Start -- db_connector
## Description

Dialog Flow DB Connector allows you to save and retrieve user dialogue states (in the form of a `Context` object) using various database backends. 

Currently, the supported options are: 
* [json](https://www.json.org/json-en.html)
* [pickle](https://docs.python.org/3/library/pickle.html)
* [shelve](https://docs.python.org/3/library/shelve.html)
* [Sqlite](https://www.sqlite.org/index.html)
* [Postgresql](https://www.postgresql.org/)
* [MySQL](https://www.mysql.com/)
* [MongoDB](https://www.mongodb.com/)
* [Redis](https://redis.io/)
* [YDB](https://ydb.tech/)

Aside from this, we offer some interfaces for saving data to your local file system. These are not meant to be used in production, but can be helpful for prototyping your application.

## Installation
```bash
pip install dff
```

Please, note that if you are going to use one of the database backends, you will have to specify an extra or install the corresponding requirements yourself.
```bash
pip install dff[redis]
pip install dff[mongodb]
pip install dff[mysql]
pip install dff[postgresql]
pip install dff[sqlite]
pip install dff[ydb]
```

## Basic example

```python
from dff.script import Context, Actor
from dff.context_storages import SQLContextStorage
from .script import some_df_script

db = SQLContextStorage("postgresql://user:password@host:port/dbname")

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

To get more advanced examples, take a look at [examples](https://github.com/deeppavlov/dialog_flow_framework/tree/dev/examples) on GitHub.

# Contributing to the Dialog Flow Framework

Please refer to [CONTRIBUTING.md](https://github.com/deeppavlov/dialog_flow_framework/blob/dev/CONTRIBUTING.md).

TODO: split README.md to addons/README.rst & split examples and docs
