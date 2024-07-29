# %% [markdown]
"""
# 3. Pipeline dict with services (basic)

The following tutorial shows `pipeline` creation from
dict and most important pipeline components.

Here, %mddoclink(api,pipeline.service.service,Service)
class, that can be used for pre- and postprocessing of messages is shown.

Pipeline's %mddoclink(api,pipeline.pipeline.pipeline,Pipeline.from_dict)
static method is used for pipeline creation (from dictionary).
"""

# %pip install chatsky

# %%
import logging

from chatsky.pipeline import Service, Pipeline

from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from chatsky.utils.testing.toy_script import HAPPY_PATH, TOY_SCRIPT

logger = logging.getLogger(__name__)


# %% [markdown]
"""
When Pipeline is created using Pydantic's `model_validate` method,
pipeline should be defined as a dictionary.
It may contain `pre-services` and 'post-services' - `ServiceGroup` objects,
basically a list of `Service` objects or more `ServiceGroup` objects,
see tutorial 4.

On pipeline execution services from `components` = 'pre-services' + actor + 'post-services'
list are run without difference between pre- and postprocessors.
`Service` object can be defined either with callable
(see tutorial 2) or with `Service` constructor / dict.
It must contain `handler` - a callable (function).

Not only Pipeline can be run using `__call__` method,
for most cases `run` method should be used.
It starts pipeline asynchronously and connects to provided messenger interface.

Here, the pipeline contains 4 services,
defined in 4 different ways with different signatures.
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
        {"handler": prepreprocess},
        preprocess,
    ],
    "post_services": Service(handler=postprocess),
}

# %%
pipeline = Pipeline.model_validate(pipeline_dict)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
