"""
Asynchronous groups and services (basic)
========================================

The following example shows pipeline asynchronous service and service group usage
"""

import asyncio
import logging

from dff.core.pipeline import Pipeline
from dff.utils.common import create_example_actor, run_example

logger = logging.getLogger(__name__)

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


async def time_consuming_service(_):
    await asyncio.sleep(0.01)


pipeline_dict = {
    "components": [
        [time_consuming_service for _ in range(0, 10)],
        create_example_actor(),
    ],
}


pipeline = Pipeline.from_dict(pipeline_dict)

if __name__ == "__main__":
    run_example(logger, pipeline=pipeline)
