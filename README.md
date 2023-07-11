
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
pip install dff[json]  # dependencies for using JSON
pip install dff[pickle] # dependencies for using Pickle
pip install dff[redis]  # dependencies for using Redis
pip install dff[mongodb]  # dependencies for using MongoDB
pip install dff[mysql]  # dependencies for using MySQL
pip install dff[postgresql]  # dependencies for using PostgreSQL
pip install dff[sqlite]  # dependencies for using SQLite
pip install dff[ydb]  # dependencies for using Yandex Database
pip install dff[telegram]  # dependencies for using Telegram
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
[tutorials](https://github.com/deeppavlov/dialog_flow_framework/tree/dev/tutorials) on GitHub.

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
[tutorials](https://github.com/deeppavlov/dialog_flow_framework/tree/dev/tutorials/context_storages) on GitHub.

# Quick Start -- df_stats

## Description

Dialog Flow Stats collects usage statistics for your conversational service and allows you to visualize them using a pre-configured dashboard for [Apache Superset](https://superset.apache.org/) or [Preset](https://preset.io/).

We provide a pre-built Superset Docker image that includes all the necessary dependencies and ensures API compatibility. 

Authorization credentials for the image can be automatically configured via environment variables.

```shell
echo 'SUPERSET_USERNAME=...' >> .env
echo 'SUPERSET_PASSWORD=...' >> .env
docker run --env-file='.env' ghcr.io/deeppavlov/superset_df_dashboard:latest
```

Currently, support is offered for multiple database types that can be used as a backend storage for your data:

* [Postgresql](https://www.postgresql.org/)
* [Clickhouse](https://clickhouse.com/)

In addition, you can use the library without any dependencies
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
from dff.pipeline import Pipeline, Service, ACTOR

from dff.stats import default_extractors
from dff.stats import OtelInstrumentor, set_logger_destination, set_tracer_destination
from dff.stats import OTLPLogExporter, OTLPSpanExporter

# initialize opentelemetry
# insecure parameter allows for SSL-independent connections
set_logger_destination(OTLPLogExporter("grpc://localhost:4317", insecure=True))
set_tracer_destination(OTLPSpanExporter("grpc://localhost:4317", insecure=True))
dff_instrumentor = OtelInstrumentor()
dff_instrumentor.instrument()

# Instrumentation is applied to pipeline's extra handlers so that their output
# gets persisted to the database. Use these handlers to report statistics
# about a particular service in the pipeline.

pipeline = Pipeline.from_dict(
    {
        "components": [
            Service(
                handler=ACTOR,
                before_handler=[default_extractors.get_timing_before],
                after_handler=[
                    default_extractors.get_timing_after,
                    default_extractors.get_current_label,
                ],
            ),
        ]
    }
)

pipeline.run()
```

## Display your data

### Adjust Dashboard Configuration

In order to run the dashboard in Apache Superset, you should update the default configuration with the credentials of your database. The output will be saved to a zip archive.

Auth credentials can be passed as command line arguments.

```bash
dff.stats cfg_from_opts --help
```

Alternatively, you can save the settings in a YAML file. 

```yaml
db:
  type: clickhousedb+connect
  name: test
  user: user
  host: localhost
  port: 5432
  table: dff_stats
```

The file should then be forwarded to the configuration script:

```bash
dff.stats cfg_from_file config.yaml --outfile=./superset_dashboard.zip
```

### Import the Dashboard Config

Log in to Superset, open the `Dashboards` tab and press the **import** button on the right of the screen. You will be prompted for the database password. If all of the database credentials match, the dashboard will appear in the dashboard list.

# Contributing to the Dialog Flow Framework

Please refer to [CONTRIBUTING.md](https://github.com/deeppavlov/dialog_flow_framework/blob/dev/CONTRIBUTING.md).
