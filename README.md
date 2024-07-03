# Chatsky

[![Documentation Status](https://github.com/deeppavlov/chatsky/workflows/build_and_publish_docs/badge.svg?branch=dev)](https://deeppavlov.github.io/chatsky)
[![Codestyle](https://github.com/deeppavlov/chatsky/workflows/codestyle/badge.svg?branch=dev)](https://github.com/deeppavlov/chatsky/actions/workflows/codestyle.yml)
[![Tests](https://github.com/deeppavlov/chatsky/workflows/test_coverage/badge.svg?branch=dev)](https://github.com/deeppavlov/chatsky/actions/workflows/test_coverage.yml)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/deeppavlov/chatsky/blob/master/LICENSE)
![Python 3.8, 3.9, 3.10, 3.11](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-green.svg)
[![PyPI](https://img.shields.io/pypi/v/chatsky)](https://pypi.org/project/chatsky/)
[![Downloads](https://pepy.tech/badge/chatsky)](https://pepy.tech/project/chatsky)

Chatsky allows you to develop conversational services.
Chatsky offers a specialized domain-specific language (DSL) for quickly writing dialogs in pure Python. The service is created by defining a special dialog graph that determines the behavior of the dialog agent. The latter is then leveraged in the Chatsky pipeline.
You can use the framework in various services such as social networks, call centers, websites, personal assistants, etc.

Chatsky, a versatile Python-based conversational service framework, can be deployed across a spectrum of platforms,
ensuring flexibility for both novice and seasoned developers:

- Cloud platforms like AWS, Azure, and GCP offer scalable environments for Chatsky,
  with options such as AWS Lambda and Azure Functions providing serverless execution.
- For containerized deployment, Docker and Kubernetes streamline the orchestration of Chatsky applications.
- Furthermore, the framework's adaptability extends to IoT ecosystems,
  making it suitable for integration with edge devices in scenarios like smart homes or industrial automation.

Whether deployed on cloud platforms, containerized environments, or directly on IoT devices,
Chatsky's accessibility and customization options make it a robust choice for developing conversational services
in the evolving landscape of Python applications and IoT connectivity.

## Why choose Chatsky

* Written in pure Python, the framework is easily accessible for both beginners and experienced developers.
* For the same reason, all the abstractions used in Chatsky can be easily customized and extended using regular language synthax.
* Chatsky offers easy and straightforward tools for state management which is as easy as setting values of a Python dictionary.
* The framework is being actively maintained and thoroughly tested. The team is open to suggestions and quickly reacts to bug reports.

# Quick Start

## System Requirements

- Supported operating systems include Ubuntu 18.04+, Windows 10+ (partial support), and MacOS Big Sur (partial support);
- Python version 3.8 or higher is necessary for proper functionality;
- A minimum of 1 GB of RAM is required for optimal performance;
- If analytics collection or database integration is intended, Docker version 20 or higher may be necessary.


## Installation

Chatsky can be installed via pip:

```bash
pip install chatsky
```

The above command will set the minimum dependencies to start working with Chatsky. 
The installation process allows the user to choose from different packages based on their dependencies, which are:
```bash
pip install chatsky[json]  # dependencies for using JSON
pip install chatsky[pickle] # dependencies for using Pickle
pip install chatsky[redis]  # dependencies for using Redis
pip install chatsky[mongodb]  # dependencies for using MongoDB
pip install chatsky[mysql]  # dependencies for using MySQL
pip install chatsky[postgresql]  # dependencies for using PostgreSQL
pip install chatsky[sqlite]  # dependencies for using SQLite
pip install chatsky[ydb]  # dependencies for using Yandex Database
pip install chatsky[telegram]  # dependencies for using Telegram
pip install chatsky[benchmark]  # dependencies for benchmarking
```

For example, if you are going to use one of the database backends,
you can specify the corresponding requirements yourself. Multiple dependencies can be installed at once, e.g.
```bash
pip install chatsky[postgresql,mysql]
```

## Basic example

The following code snippet builds a simplistic chat bot that replies with messages
``Hi!`` and ``OK`` depending on user input, which only takes a few lines of code.
All the abstractions used in this example are thoroughly explained in the dedicated
[user guide](https://deeppavlov.github.io/chatsky/user_guides/basic_conceptions.html).

```python
from chatsky.script import GLOBAL, TRANSITIONS, RESPONSE, Message
from chatsky.pipeline import Pipeline
import chatsky.script.conditions.std_conditions as cnd

# create a dialog script
script = {
    GLOBAL: {
        TRANSITIONS: {
            ("flow", "node_hi"): cnd.exact_match("Hi"),
            ("flow", "node_ok"): cnd.true()
        }
    },
    "flow": {
        "node_hi": {RESPONSE: Message("Hi!")},
        "node_ok": {RESPONSE: Message("OK")},
    },
}

# init pipeline
pipeline = Pipeline.from_script(script, start_label=("flow", "node_hi"))


def turn_handler(in_request: Message, pipeline: Pipeline) -> Message:
    # Pass user request into pipeline and get dialog context (message history)
    # The pipeline will automatically choose the correct response using script
    ctx = pipeline(in_request, 0)
    # Get last response from the context
    out_response = ctx.last_response
    return out_response


while True:
    in_request = input("Your message: ")
    out_response = turn_handler(Message(in_request), pipeline)
    print("Response: ", out_response.text)
```

When you run this code, you get similar output:
```
Your message: hi
Response:  OK
Your message: Hi
Response:  Hi!
Your message: ok
Response:  OK
Your message: ok
Response:  OK
```

More advanced examples are available as a part of documentation:
[tutorials](https://deeppavlov.github.io/chatsky/tutorials.html).

## Further steps

To further explore the API of the framework, you can make use of the [detailed documentation](https://deeppavlov.github.io/chatsky/index.html). 
Broken down into several sections to highlight all the aspects of development with Chatsky,
the documentation for the library is constantly available online.

# Contributing to Chatsky

We are open to accepting pull requests and bug reports.
Please refer to [CONTRIBUTING.md](https://github.com/deeppavlov/chatsky/blob/master/CONTRIBUTING.md).

# License

Chatsky is distributed under the terms of the [Apache License 2.0](https://github.com/deeppavlov/chatsky/blob/master/LICENSE).
