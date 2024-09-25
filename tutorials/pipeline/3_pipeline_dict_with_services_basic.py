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
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="")
logger = logging.getLogger(__name__)


# %% [markdown]
"""
When a `Pipeline` is created using Pydantic's `model_validate` method or the
`Pipeline` constructor, it should be defined as a dictionary
with a specific structure that includes `script`,
`start_label` and `fallback_label`, see `Script` tutorials.

Optional Pipeline parameters:

* `messenger_interface` - `MessengerInterface` instance,
        is used to connect to channel and transfer IO to user.
* `context_storage` - Place to store dialog contexts
        (dictionary or a `DBContextStorage` instance).
* `pre-services` - A `ServiceGroup` object,
        essentially a list of `Service` objects or more `ServiceGroup` objects,
        see [tutorial 4](
        %doclink(tutorial,pipeline.4_groups_and_conditions_basic)).
* `post-services` - A `ServiceGroup` object,
        essentially a list of `Service` objects or more `ServiceGroup` objects,
        see [tutorial 4](
        %doclink(tutorial,pipeline.4_groups_and_conditions_basic)).
* `before_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See [tutorial 6](%doclink(tutorial,pipeline.6_extra_handlers_basic))
        and [tutorial 7](
        %doclink(tutorial,pipeline.7_extra_handlers_and_extensions)).
* `after_handler` - a list of `ExtraHandlerFunction` objects or
        a `ComponentExtraHandler` object.
        See [tutorial 6](%doclink(tutorial,pipeline.6_extra_handlers_basic))
        and [tutorial 7](
        %doclink(tutorial,pipeline.7_extra_handlers_and_extensions)).
* `timeout` - Pipeline timeout, see [tutorial 5](
        %doclink(tutorial,pipeline.5_asynchronous_groups_and_services)).

On pipeline execution services from
`components` = 'pre-services' + actor + 'post-services'
list are run without difference between pre- and postprocessors.
`Service` object can be defined either with callable
(see [tutorial 2](%doclink(tutorial,pipeline.2_pre_and_post_processors)))
or with `Service` constructor / dict.
It must contain `handler` - a callable (function).

Services can also be defined as subclasses of `Service`,
allowing access to the `self` object for logging and
additional information. (see [full tutorial](
%doclink(tutorial,pipeline.3_pipeline_dict_with_services_full)))

While a Pipeline can be executed using the  `__call__` method,
for most cases `run` method should be used.
It starts the pipeline asynchronously and connects
to the provided messenger interface.

In this example, the pipeline contains three services,
which send some information to the logger.
"""


# %%
def prepreprocess(_):
    logger.info(
        "prepreprocessor Service running (defined as a dict)"
    )


def preprocess(_):
    logger.info(
        "preprocessor Service running (defined as a callable)"
    )


def postprocess(_):
    logger.info("postprocessor Service running (defined as an object)")


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
