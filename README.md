
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

# Quick Start -- df_stats

## Description

Dialog Flow Stats collects usage statistics for your conversational service and allows you to visualize those using a pre-configured dashboard for [Apache Superset](https://superset.apache.org/) or [Preset](https://preset.io/).

There are multiple ways to deploy an Apache Superset instance: you can install it locally or use a [Docker image](https://hub.docker.com/r/apache/superset) with docker or docker-compose. 
See the [Superset documentation](https://superset.apache.org/docs/databases/installing-database-drivers/) for more info.

Currently, support is offered for multiple database types that can be used as a backend storage for your data:

* [Postgresql](https://www.postgresql.org/)
* [Clickhouse](https://clickhouse.com/)

As an addition, you can use the library without any dependencies
to save your service logs to `csv`-formatted files.

## Installation

```bash
pip install dff[stats] # csv-only, no connection to Superset
pip install dff[stats,clickhouse]
pip install dff[stats,postgresql]
```

## Setting up a pipeline

```python
# import dependencies
from dff.stats import StatsStorage
from dff.stats import default_extractor_pool

# Extractor pools are namespaces that contain handler functions
# Like all functions of this kind, they can be used in a pipeline
# In the following example, the handlers measure the running time of the actor
actor = Actor(...)
actor_service = to_service(
    before_handler=[default_extractor_pool["extract_timing_before"]],
    after_handler=[default_extractor_pool["extract_timing_after"]]
)(actor)

pipeline = Pipeline.from_dict(
    {
        "components": [
            Service(handler=actor_service),
        ]
    }
)

# Define a destination for stats saving
db_uri = "postgresql://user:password@host:5432/default"
# for clickhouse:
# db_uri = "clickhouse://user:password@host:8123/default"
# for csv:
# db_uri = "csv://file.csv"
stats = StatsStorage.from_uri(db_uri)
# update the stats object
stats.add_extractor_pool(default_extractor_pool)
pipeline.run()
```

## Display your data

### Adjust Dashboard Configuration

In order to run the dashboard in Apache Superset, you should update the default configuration with the credentials of your database. The output will be saved to a zip archive.

It can be done through the  CLI:

```bash
dff.stats --help
```

An alternative way is to save the settings in a YAML file. 

```yaml
db:
  type: clickhousedb+connect
  name: test
  user: user
  host: localhost
  port: 5432
  table: dff_stats
```

You can forward the file to the script like this:

```bash
dff.stats cfg_from_file config.yaml --outfile=./superset_dashboard.zip
```

### Import the Dashboard Config

Log in to Superset, open the `Dashboards` tab and press the **import** button on the right of the screen. You will be prompted for the database password. If all of the database credentials match, the dashboard will appear in the dashboard list.

# Contributing to the Dialog Flow Framework

Please refer to [CONTRIBUTING.md](https://github.com/deeppavlov/dialog_flow_framework/blob/dev/CONTRIBUTING.md).