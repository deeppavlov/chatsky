# %%
import random
import asyncio
from tqdm import tqdm
from dff.script import Context, Message, RESPONSE, TRANSITIONS
from dff.script import conditions as cnd
from dff.pipeline import Pipeline, ACTOR, Service
from dff.stats import (
    OtelInstrumentor,
    default_extractors
)

# %%
# instrumentation code
dff_instrumentor = OtelInstrumentor.from_url("grpc://localhost:4317", insecure=True)
dff_instrumentor.instrument()


def numbered_flow_factory(number: int):
    return {
        f"node_{str(n)}": {
            RESPONSE: Message(text=f"node_{str(number)}_{str(n)}"),
            TRANSITIONS: {f"node_{str(n+1)}": cnd.true()} if n != 4 else {("root", "fallback"): cnd.true()},
        }
        for n in range(5)
    }


numbered_script = {
    "root": {
        "start": {
            RESPONSE: Message(text="Hi"),
            TRANSITIONS: {
                lambda ctx, pipeline: (f"flow_{random.choice(range(1, 11))}", "node_1"): cnd.exact_match(
                    Message(text="hi")
                ),
            },
        },
        "fallback": {RESPONSE: Message(text="Oops")},
    },
    **{f"flow_{str(n)}": numbered_flow_factory(n) for n in range(1, 11)},
}

transitions_script = {
    "root": {
        "start": {
            RESPONSE: Message(text="Hi"),
            TRANSITIONS: {
                ("flow_1", "node"): cnd.exact_match(Message(text="hi")),
            },
        },
        "fallback": {RESPONSE: Message(text="Oops")},
    },
    **{
        f"flow_{str(num)}": {
            "node": {
                RESPONSE: Message(text="Message."),
                TRANSITIONS: {(f"flow_{str(num+1)}", "node"): cnd.true()}
                if num != 100
                else {("root", "fallback"): cnd.true()},
            }
        }
        for num in range(1, 101)
    },
}


transition_test_pipeline = Pipeline.from_dict(
    {
        "script": transitions_script,
        "start_label": ("root", "start"),
        "fallback_label": ("root", "fallback"),
        "components": [
            Service(
                handler=ACTOR,
                after_handler=[
                    default_extractors.get_current_label,
                ],
            ),
        ],
    }
)

numbered_test_pipeline = Pipeline.from_dict(
    {
        "script": numbered_script,
        "start_label": ("root", "start"),
        "fallback_label": ("root", "fallback"),
        "components": [
            Service(
                handler=ACTOR,
                after_handler=[
                    default_extractors.get_current_label,
                ],
            ),
        ],
    }
)


# %%
async def worker(pipeline: Pipeline, queue: asyncio.Queue):
    """
    Worker function for dispatching one client message.
    The client message is chosen randomly from a predetermined set of options.
    It simulates pauses in between messages by calling the sleep function.

    The function also starts a new dialog as a new user, if the current dialog
    ended in the fallback_node.

    :param queue: Queue for sharing context variables.
    """
    ctx: Context = await queue.get()
    in_message = Message(text="Hi")
    await asyncio.sleep(random.random() * 3)
    ctx = await pipeline._run_pipeline(in_message, ctx.id)
    await asyncio.sleep(random.random() * 3)
    await queue.put(ctx)


# %%
# main loop
async def loop(pipeline: Pipeline, n_iterations: int = 10, n_workers: int = 10):
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
        await asyncio.gather(*(worker(pipeline, ctxs) for _ in range(n_workers)))


if __name__ == "__main__":
    asyncio.run(loop(numbered_test_pipeline))
