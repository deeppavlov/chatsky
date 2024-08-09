#!/usr/bin/env python
# %% [markdown]
"""
This script demonstrates various instrumentation capabilities.
It also provides data for the dashboard emulating simultaneous queries
to the service by multiple users.

"""

# %%
import random
import asyncio
from tqdm import tqdm
from chatsky.script import Context, Message
from chatsky.pipeline import Pipeline, Service, ExtraHandlerRuntimeInfo, GlobalExtraHandlerType
from chatsky.stats import (
    default_extractors,
    OtelInstrumentor,
)
from chatsky.utils.testing.toy_script import MULTIFLOW_SCRIPT, MULTIFLOW_REQUEST_OPTIONS

# %%
# instrumentation code
chatsky_instrumentor = OtelInstrumentor.from_url("grpc://localhost:4317", insecure=True)
chatsky_instrumentor.instrument()


def slot_processor_1(ctx: Context):
    ctx.misc["slots"] = {**ctx.misc.get("slots", {}), "rating": random.randint(1, 10)}


def slot_processor_2(ctx: Context):
    ctx.misc["slots"] = {
        **ctx.misc.get("slots", {}),
        "current_topic": random.choice(["films", "games", "books", "smalltalk"]),
    }


@chatsky_instrumentor
async def get_slots(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    return ctx.misc["slots"]


def confidence_processor(ctx: Context):
    ctx.misc["response_confidence"] = random.random()


@chatsky_instrumentor
async def get_confidence(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
    data = {"response_confidence": ctx.misc["response_confidence"]}
    return data


# %%
pipeline = Pipeline.model_validate(
    {
        "script": MULTIFLOW_SCRIPT,
        "start_label": ("root", "start"),
        "fallback_label": ("root", "fallback"),
        "pre_services": [
            Service(handler=slot_processor_1, after_handler=[get_slots]),
            Service(handler=slot_processor_2, after_handler=[get_slots]),
        ],
        "post_services": Service(handler=confidence_processor, after_handler=[get_confidence]),
    }
)
pipeline.actor.add_extra_handler(GlobalExtraHandlerType.BEFORE, default_extractors.get_timing_before)
pipeline.actor.add_extra_handler(GlobalExtraHandlerType.AFTER, default_extractors.get_timing_after)
pipeline.actor.add_extra_handler(GlobalExtraHandlerType.AFTER, default_extractors.get_current_label)
pipeline.actor.add_extra_handler(GlobalExtraHandlerType.AFTER, default_extractors.get_last_request)
pipeline.actor.add_extra_handler(GlobalExtraHandlerType.AFTER, default_extractors.get_last_response)


# %%
async def worker(queue: asyncio.Queue):
    """
    Worker function for dispatching one client message.
    The client message is chosen randomly from a predetermined set of options.
    It simulates pauses in between messages by calling the sleep function.

    The function also starts a new dialog as a new user, if the current dialog
    ended in the fallback_node.

    :param queue: Queue for sharing context variables.
    """
    ctx: Context = await queue.get()
    label = ctx.last_label if ctx.last_label else pipeline.actor.fallback_label
    flow, node = label[:2]
    if [flow, node] == ["root", "fallback"]:
        await asyncio.sleep(random.random() * 3)
        ctx = Context()
        flow, node = ["root", "start"]
    answers = list(MULTIFLOW_REQUEST_OPTIONS.get(flow, {}).get(node, []))
    in_text = random.choice(answers) if answers else "go to fallback"
    in_message = Message(in_text)
    await asyncio.sleep(random.random() * 3)
    ctx = await pipeline._run_pipeline(in_message, ctx.id)
    await asyncio.sleep(random.random() * 3)
    await queue.put(ctx)


# %%
# main loop
async def main(n_iterations: int = 100, n_workers: int = 4):
    """
    The main loop that runs one or more worker coroutines in parallel.

    :param n_iterations: Total number of coroutine runs.
    :param n_workers: Number of parallelized coroutine runs.
    """
    ctxs = asyncio.Queue()
    parallel_iterations = n_iterations // n_workers
    for _ in range(n_workers):
        await ctxs.put(Context())
    for _ in tqdm(range(parallel_iterations)):
        await asyncio.gather(*(worker(ctxs) for _ in range(n_workers)))


if __name__ == "__main__":
    asyncio.run(main())
