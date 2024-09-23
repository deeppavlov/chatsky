# %% [markdown]
"""
# 3. Pipeline dict with services (basic)

The following tutorial shows `pipeline` creation from
dict and most important pipeline components.

Here, %mddoclink(api,core.service.service,Service)
class, that can be used for pre- and postprocessing of messages is shown.

%mddoclink(api,core.pipeline,Pipeline)'s
constructor method is used for pipeline creation (directly or from dictionary).
"""

# %pip install chatsky

# %%
import logging
import sys
from importlib import reload

from chatsky import Pipeline
from chatsky.core.service import Service

from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
)
from chatsky.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

reload(logging)
logging.basicConfig(
    stream=sys.stdout, format="", level=logging.INFO, datefmt=None
)
logger = logging.getLogger(__name__)


# %% [markdown]
"""
When Pipeline is created using it's constructor method or
Pydantic's `model_validate` method,
`Pipeline` should be defined as a dictionary of a particular structure,
which must contain `script`, `start_label` and `fallback_label`,
see `Script` tutorials.

Optional Pipeline parameters:
* `messenger_interface` - `MessengerInterface` instance,
        is used to connect to channel and transfer IO to user.
* `context_storage` - Place to store dialog contexts
        (dictionary or a `DBContextStorage` instance).
* `pre-services` - A `ServiceGroup` object,
        basically a list of `Service` objects or more `ServiceGroup` objects,
        see tutorial 4.
* `post-services` - A `ServiceGroup` object,
        basically a list of `Service` objects or more `ServiceGroup` objects,
        see tutorial 4.
* `before_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See tutorials 6 and 7.
* `after_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See tutorials 6 and 7.
* `timeout` - Pipeline timeout, see tutorial 5.

On pipeline execution services from
`components` = 'pre-services' + actor + 'post-services'
list are run without difference between pre- and postprocessors.
`Service` object can be defined either with callable
(see tutorial 2) or with `Service` constructor / dict.
It must contain `handler` - a callable (function).

Services can also be defined as a child class of `Service`, so that
you can get access to the `self` object to get more
information about your `Service` and log it. (see full tutorial)

Not only Pipeline can be run using `__call__` method,
for most cases `run` method should be used.
It starts pipeline asynchronously and connects to provided messenger interface.

Here, the pipeline contains 3 services,
which just send some info to the logger.
"""


# %%
def prepreprocess(_):
    logger.info(
        "preprocession intent-detection Service running (defined as a dict)"
    )


def preprocess(_):
    logger.info(
        "another preprocession web-based annotator Service "
        "(defined as a callable)"
    )


def postprocess(_):
    logger.info("postprocession Service (defined as an object)")


# %%
pipeline_dict = {
    "script": TOY_SCRIPT,
    "start_label": ("greeting_flow", "start_node"),
    "fallback_label": ("greeting_flow", "fallback_node"),
    "pre_services": [
        {
            "handler": prepreprocess,
            "name": "prepreprocessor",
        },
        preprocess,
    ],
    "post_services": Service(handler=postprocess, name="postprocessor"),
}

# %%
pipeline = Pipeline(**pipeline_dict)
# or
# pipeline = Pipeline.model_validate(pipeline_dict)


if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)
    if is_interactive_mode():
        pipeline.run()
