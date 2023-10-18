
# Dialog Flow Framework

The Dialog Flow Framework (DFF) allows you to write conversational services.
The service is written by defining a special dialog graph that describes the behavior of the dialog service.
The dialog graph contains the dialog script. DFF offers a specialized language (DSL) for quickly writing dialog graphs.
You can use it in services such as writing skills for Amazon Alexa, etc., chatbots for social networks, website call centers, etc.

[![Documentation Status](https://github.com/deeppavlov/dialog_flow_framework/workflows/build_and_publish_docs/badge.svg)](https://deeppavlov.github.io/dialog_flow_framework)
[![Codestyle](https://github.com/deeppavlov/dialog_flow_framework/workflows/codestyle/badge.svg)](https://github.com/deeppavlov/dialog_flow_framework/actions/workflows/codestyle.yml)
[![Tests](https://github.com/deeppavlov/dialog_flow_framework/workflows/test_coverage/badge.svg)](https://github.com/deeppavlov/dialog_flow_framework/actions/workflows/test_coverage.yml)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/deeppavlov/dialog_flow_framework/blob/master/LICENSE)
![Python 3.8, 3.9, 3.10, 3.11](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-green.svg)
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
pip install dff[json]  # dependencies for using JSON
pip install dff[pickle] # dependencies for using Pickle
pip install dff[redis]  # dependencies for using Redis
pip install dff[mongodb]  # dependencies for using MongoDB
pip install dff[mysql]  # dependencies for using MySQL
pip install dff[postgresql]  # dependencies for using PostgreSQL
pip install dff[sqlite]  # dependencies for using SQLite
pip install dff[ydb]  # dependencies for using Yandex Database
pip install dff[telegram]  # dependencies for using Telegram
pip install dff[benchmark]  # dependencies for benchmarking
pip install dff[full]  # full dependencies including all options above
pip install dff[tests]  # dependencies for running tests
pip install dff[test_full]  # full dependencies for running all tests (all options above)
pip install dff[tutorials]  # dependencies for running tutorials (all options above)
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
from dff.script import GLOBAL, TRANSITIONS, RESPONSE, Context, Message
from dff.pipeline import Pipeline
import dff.script.conditions.std_conditions as cnd
from typing import Tuple

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

# init pipeline
pipeline = Pipeline.from_script(script, start_label=("flow", "node_hi"))


# handler requests
def turn_handler(in_request: Message, pipeline: Pipeline) -> Tuple[Message, Context]:
    # Pass the next request of user into pipeline and it returns updated context with actor response
    ctx = pipeline(in_request, 0)
    # Get last actor response from the context
    out_response = ctx.last_response
    # The next condition branching needs for testing
    return out_response, ctx


while True:
    in_request = input("type your answer: ")
    out_response, ctx = turn_handler(Message(text=in_request), pipeline)
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
[tutorials](https://github.com/deeppavlov/dialog_flow_framework/tree/master/tutorials) on GitHub.

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
from dff.script import Context
from dff.pipeline import Pipeline
from dff.context_storages import SQLContextStorage
from .script import some_df_script

db = SQLContextStorage("postgresql+asyncpg://user:password@host:port/dbname")

pipeline = Pipeline.from_script(some_df_script, start_label=("root", "start"), fallback_label=("root", "fallback"))


def handle_request(request):
    user_id = request.args["user_id"]
    new_context = pipeline(request, user_id)
    return new_context.last_response

```

To get more advanced examples, take a look at
[tutorials](https://github.com/deeppavlov/dialog_flow_framework/tree/master/tutorials/context_storages) on GitHub.

# Contributing to the Dialog Flow Framework

Please refer to [CONTRIBUTING.md](https://github.com/deeppavlov/dialog_flow_framework/blob/master/CONTRIBUTING.md).
