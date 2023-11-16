
# Dialog Flow Framework

The Dialog Flow Framework (DFF) allows you to develop conversational services.
DFF offers a specialized domain-specific language (DSL) for quickly writing dialogs in pure Python. The service is created by defining a special dialog graph that determines the behavior of the dialog agent. The latter is then leveraged in the DFF pipeline.
You can use the framework in various services, such as Amazon Alexa skills, chatbots for social networks, call centers, etc.

## Why choose DFF

* Written in pure Python, the framework is easily accessible for both beginners and experienced developers.
* For the same reason, all the abstractions used in DFF can be easily customized and extended using regular language synthax.
* DFF offers easy and straightforward tools for state management which is as easy as setting values of a Python dictionary.
* The framework is being actively maintained and thoroughly tested. The team is open to suggestions and quickly reacts to bug reports.

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

The following code snippet builds a simplistic chat bot that replies with messages
``Hi!!!`` and ``Okey`` depending on user input, which only takes a few lines of code.
All the abstractions used in this example are thoroughly explained in the dedicated
[user guide](https://deeppavlov.github.io/dialog_flow_framework/user_guides/basic_conceptions.html).

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

More advanced examples are available as a part of documentation:
[tutorials](https://deeppavlov.github.io/dialog_flow_framework/tutorials.html).

## Further steps

To further explore the API of the framework, you can make use of the detailed documentation. 
Broken down into several sections to highlight all the aspects of development with DFF,
the documentation for the library is constantly available online.

* [API reference](https://deeppavlov.github.io/dialog_flow_framework/reference.html)
* [Tutorials: interactive jupyter notebooks](https://deeppavlov.github.io/dialog_flow_framework/tutorials.html)
* [User guides: code-supplemented instructions](https://deeppavlov.github.io/dialog_flow_framework/user_guides.html)

You can also take a look at demonstration projects that showcase how DFF pipelines
can be integrated into web applications and leverage external APIs.

* [Project repository](https://github.com/deeppavlov/dialog_flow_demo)

# Contributing to the Dialog Flow Framework

We are open to accepting pull requests and bug reports.
Please refer to [CONTRIBUTING.md](https://github.com/deeppavlov/dialog_flow_framework/blob/master/CONTRIBUTING.md).
