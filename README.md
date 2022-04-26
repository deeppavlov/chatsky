
# Dialog Flow Engine

The Dialog Flow Engine (DFE) allows you to write conversational services. The service is written by defining a special dialog graph that describes the behavior of the dialog service. The dialog graph contains the dialog script. DFE offers a specialized language (DSL) for quickly writing dialog graphs. You can use it in such services for writing skills for Amazon Alexa and etc, chat-bots for social networks, websites call-centers and etc. 

[![Documentation Status](https://readthedocs.org/projects/dialog-flow-engine/badge/?version=latest)](https://readthedocs.org/projects/dialog-flow-engine/badge/?version=latest)
[![Codestyle](https://github.com/deepmipt/dialog_flow_engine/workflows/codestyle/badge.svg)](https://github.com/deepmipt/dialog_flow_engine/actions)
[![Tests](https://github.com/deepmipt/dialog_flow_engine/workflows/test_coverage/badge.svg)](https://github.com/deepmipt/dialog_flow_engine/actions)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/deepmipt/dialog_flow_engine/blob/master/LICENSE)
![Python 3.6, 3.7, 3.8, 3.9](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-green.svg)
[![PyPI](https://img.shields.io/pypi/v/df_engine)](https://pypi.org/project/df_engine/)
[![Downloads](https://pepy.tech/badge/df_engine)](https://pepy.tech/project/df_engine)

# Quick Start
## Installation
```bash
pip install df_engine
```

## Basic example
```python
from df_engine.core.keywords import GLOBAL, TRANSITIONS, RESPONSE
from df_engine.core import Context, Actor
import df_engine.conditions as cnd
from typing import Union

# create script of dialog
script = {
    GLOBAL: {TRANSITIONS: {("flow", "node_hi"): cnd.exact_match("Hi"), ("flow", "node_ok"): cnd.true()}},
    "flow": {
        "node_hi": {RESPONSE: "Hi!!!"},
        "node_ok": {RESPONSE: "Okey"},
    },
}

# init actor
actor = Actor(script, start_label=("flow", "node_hi"))


# handler requests
def turn_handler(in_request: str, ctx: Union[Context, dict], actor: Actor):
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
    out_response, ctx = turn_handler(in_request, ctx, actor)
    print(out_response)

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

To get more advanced examples, take a look at [examples](https://github.com/deepmipt/dialog_flow_engine/tree/dev/examples) on GitHub.

# Contributing to the Dialog Flow Engine

Please refer to [CONTRIBUTING.md](https://github.com/deepmipt/dialog_flow_engine/blob/dev/CONTRIBUTING.md).
