import random
import asyncio
from tqdm import tqdm
from dff.script import RESPONSE, TRANSITIONS, Context, Message
from dff.script import conditions as cnd
from dff.pipeline import Pipeline, Service, ACTOR
from dff.stats import (
    default_extractors,
    OtelInstrumentor,
)

dff_instrumentor = OtelInstrumentor.from_url("grpc://localhost:4317", insecure=True)
dff_instrumentor.instrument()

transitions = {
    "root": {
        "start": [
            "hi",
            "i like animals",
            "let's talk about animals",
        ]
    },
    "animals": {
        "have_pets": ["yes"],
        "like_animals": ["yes"],
        "what_animal": ["bird", "dog"],
        "ask_about_breed": ["pereat", "bulldog", "i do not known"],
    },
    "news": {
        "what_news": ["science", "sport"],
        "ask_about_science": ["yes", "let's change the topic"],
        "science_news": ["ok", "let's change the topic"],
        "ask_about_sport": ["yes", "let's change the topic"],
        "sport_news": ["ok", "let's change the topic"],
    },
    "small_talk": {
        "ask_some_questions": [
            "fine",
            "let's talk about animals",
            "let's talk about news",
        ],
        "ask_talk_about": ["dog", "let's talk about news"],
    },
}
# a dialog script
script = {
    "root": {
        "start": {
            RESPONSE: Message(text="Hi"),
            TRANSITIONS: {
                ("small_talk", "ask_some_questions"): cnd.exact_match(Message(text="hi")),
                ("animals", "have_pets"): cnd.exact_match(Message(text="i like animals")),
                ("animals", "like_animals"): cnd.exact_match(
                    Message(text="let's talk about animals")
                ),
                ("news", "what_news"): cnd.exact_match(Message(text="let's talk about news")),
            },
        },
        "fallback": {RESPONSE: Message(text="Oops")},
    },
    "animals": {
        "have_pets": {
            RESPONSE: Message(text="do you have pets?"),
            TRANSITIONS: {"what_animal": cnd.exact_match(Message(text="yes"))},
        },
        "like_animals": {
            RESPONSE: Message(text="do you like it?"),
            TRANSITIONS: {"what_animal": cnd.exact_match(Message(text="yes"))},
        },
        "what_animal": {
            RESPONSE: Message(text="what animals do you have?"),
            TRANSITIONS: {
                "ask_about_color": cnd.exact_match(Message(text="bird")),
                "ask_about_breed": cnd.exact_match(Message(text="dog")),
            },
        },
        "ask_about_color": {RESPONSE: Message(text="what color is it")},
        "ask_about_breed": {
            RESPONSE: Message(text="what is this breed?"),
            TRANSITIONS: {
                "ask_about_breed": cnd.exact_match(Message(text="pereat")),
                "tell_fact_about_breed": cnd.exact_match(Message(text="bulldog")),
                "ask_about_training": cnd.exact_match(Message(text="i do not known")),
            },
        },
        "tell_fact_about_breed": {
            RESPONSE: Message(
                text="Bulldogs appeared in England as specialized bull-baiting dogs. "
            ),
        },
        "ask_about_training": {RESPONSE: Message(text="Do you train your dog? ")},
    },
    "news": {
        "what_news": {
            RESPONSE: Message(text="what kind of news do you prefer?"),
            TRANSITIONS: {
                "ask_about_science": cnd.exact_match(Message(text="science")),
                "ask_about_sport": cnd.exact_match(Message(text="sport")),
            },
        },
        "ask_about_science": {
            RESPONSE: Message(text="i got news about science, do you want to hear?"),
            TRANSITIONS: {
                "science_news": cnd.exact_match(Message(text="yes")),
                ("small_talk", "ask_some_questions"): cnd.exact_match(
                    Message(text="let's change the topic")
                ),
            },
        },
        "science_news": {
            RESPONSE: Message(text="This is science news"),
            TRANSITIONS: {
                "what_news": cnd.exact_match(Message(text="ok")),
                ("small_talk", "ask_some_questions"): cnd.exact_match(
                    Message(text="let's change the topic")
                ),
            },
        },
        "ask_about_sport": {
            RESPONSE: Message(text="i got news about sport, do you want to hear?"),
            TRANSITIONS: {
                "sport_news": cnd.exact_match(Message(text="yes")),
                ("small_talk", "ask_some_questions"): cnd.exact_match(
                    Message(text="let's change the topic")
                ),
            },
        },
        "sport_news": {
            RESPONSE: Message(text="This is sport news"),
            TRANSITIONS: {
                "what_news": cnd.exact_match(Message(text="ok")),
                ("small_talk", "ask_some_questions"): cnd.exact_match(
                    Message(text="let's change the topic")
                ),
            },
        },
    },
    "small_talk": {
        "ask_some_questions": {
            RESPONSE: Message(text="how are you"),
            TRANSITIONS: {
                "ask_talk_about": cnd.exact_match(Message(text="fine")),
                ("animals", "like_animals"): cnd.exact_match(
                    Message(text="let's talk about animals")
                ),
                ("news", "what_news"): cnd.exact_match(Message(text="let's talk about news")),
            },
        },
        "ask_talk_about": {
            RESPONSE: Message(text="what do you want to talk about"),
            TRANSITIONS: {
                ("animals", "like_animals"): cnd.exact_match(Message(text="dog")),
                ("news", "what_news"): cnd.exact_match(Message(text="let's talk about news")),
            },
        },
    },
}

pipeline = Pipeline.from_dict(
    {
        "script": script,
        "start_label": ("root", "start"),
        "fallback_label": ("root", "fallback"),
        "components": [
            Service(
                handler=ACTOR,
                before_handler=[default_extractors.get_timing_before],
                after_handler=[
                    default_extractors.get_timing_after,
                    default_extractors.get_current_label,
                ],
            ),
        ],
    }
)


async def worker(queue: asyncio.Queue):
    ctx: Context = await queue.get()
    label = ctx.last_label if ctx.last_label else pipeline.actor.fallback_label
    flow, node = label[:2]
    if [flow, node] == ["root", "fallback"]:
        ctx = Context()
        flow, node = ["root", "start"]
    answers = list(transitions.get(flow, {}).get(node, []))
    in_text = random.choice(answers) if answers else "go to fallback"
    in_message = Message(text=in_text)
    rand_interval = float(random.randint(0, 1)) + random.random()
    await asyncio.sleep(rand_interval)
    ctx = await pipeline._run_pipeline(in_message, ctx.id)
    rand_interval = float(random.randint(0, 1)) + random.random()
    await asyncio.sleep(rand_interval)
    await queue.put(ctx)


async def main(n_iterations: int = 25):
    ctxs = asyncio.Queue()
    for _ in range(4):
        await ctxs.put(Context())
    for _ in tqdm(range(n_iterations)):
        await asyncio.gather(*(worker(ctxs) for _ in range(4)))


if __name__ == "__main__":
    asyncio.run(main())
