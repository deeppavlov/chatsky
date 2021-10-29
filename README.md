[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/deepmipt/dff/blob/master/LICENSE)
![Python 3.6, 3.7, 3.8, 3.9](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-green.svg)
[![Downloads](https://pepy.tech/badge/dff)](https://pepy.tech/project/dff)
# Dialog Flow Framework

The Dialog Flow Framework (DFF) is a dialogue systems development environment that supports both rapid prototyping and long-term team development workflow for dialogue systems. A simple structure allows easily building and visualizing a dialogue graph.

# Links
[Github](https://github.com/deepmipt/dialog_flow_framework)

# Quick Start

## Installation
```bash
pip install dff
```

## Basic example
```python
from dff.core.keywords import GLOBAL, TRANSITIONS, RESPONSE
from dff.core import Context, Actor
import dff.conditions as cnd
from typing import Union

# create plot of dialog
plot = {
    GLOBAL: {TRANSITIONS: {("flow", "node_hi"): cnd.exact_match("Hi"), ("flow", "node_ok"): cnd.true()}},
    "flow": {
        "node_hi": {RESPONSE: "Hi!!!"},
        "node_ok": {RESPONSE: "Okey"},
    },
}

# init actor
actor = Actor(plot, start_label=("flow", "node_hi"))


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

To get more advanced examples, take a look at [examples](https://github.com/deepmipt/dialog_flow_framework/tree/dev/examples) on GitHub.

## Extentions 
<!-- ### List of extentions -->
<!-- ### Your own extention -->

# Contributing to the Dialog Flow Framework

Please refer to [CONTRIBUTING.md](https://github.com/deepmipt/dialog_flow_framework/dev/CONTRIBUTING.md).