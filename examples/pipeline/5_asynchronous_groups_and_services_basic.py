"""
Asynchronous groups and services (basic)
========================================

The following example shows pipeline asynchronous service and service group usage
"""

import asyncio
import logging

from dff.core.engine.core import Actor

from dff.core.pipeline import Pipeline
from examples.pipeline._pipeline_utils import SCRIPT, should_auto_execute, auto_run_pipeline

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

"""
Services and service groups can be synchronous and asynchronous.
In synchronous service groups services are executed consequently.
In asynchronous service groups all services are executed simultaneously.

Service can be asynchronous if its handler is an async function.
Service group can be asynchronous if all services and service groups inside it are asynchronous.

Here there is an asynchronous service group, that contains 10 services, each of them should sleep for 0.01 of a second.
However, as the group is asynchronous, it is being executed for 0.01 of a second in total.
Service group `pipeline` can't be asynchronous because actor is synchronous.
"""


actor = Actor(
    SCRIPT,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


async def time_consuming_service(_):
    await asyncio.sleep(0.01)


pipeline_dict = {
    "components": [
        [time_consuming_service for _ in range(0, 10)],
        actor,
    ],
}


pipeline = Pipeline.from_dict(pipeline_dict)

if __name__ == "__main__":
    if should_auto_execute():
        auto_run_pipeline(pipeline, logger=logger)
    else:
        pipeline.run()
