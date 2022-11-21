from dff.core.engine.core import Context, Actor
from dff.core.engine.labels import repeat
from dff.core.engine.conditions import true
from dff.core.engine.core.keywords import RESPONSE, TRANSITIONS


def cache_test(cached_response, cache):

    ctx = Context()
    ctx.add_label(("flow", "node1"))

    def response(ctx: Context, _: Actor, *__, **___):
        if ctx.validation:
            return ""
        return f"{cached_response(1)}-{cached_response(1)}-{cached_response(1)}-{cached_response(2)}"

    script = {"flow": {"node1": {TRANSITIONS: {repeat(): true()}, RESPONSE: response}}}
    actor = Actor(script=script, start_label=("flow", "node1"), fallback_label=("flow", "node1"))
    ctx.add_request("text")
    ctx = actor(ctx)
    assert ctx.last_response == "1-1-1-2"
    ctx.add_request("text")
    ctx = actor(ctx)
    assert ctx.last_response == "1-1-1-2"
    actor = cache.update_actor_handlers(actor)
    ctx.add_request("text")
    ctx = actor(ctx)
    assert ctx.last_response == "3-3-3-4"
    ctx.add_request("text")
    ctx = actor(ctx)
    assert ctx.last_response == "5-5-5-6"


def test_caching():
    cache = OneTurnCache()

    external_data = {"counter": 0}

    @cache.cache
    def cached_response(_):
        external_data["counter"] += 1
        return external_data["counter"]

    cache_test(cached_response, cache)
    cache = OneTurnCache()

    external_data = {"counter": 0}

    @cache.lru_cache(maxsize=32)
    def cached_response(_):
        external_data["counter"] += 1
        return external_data["counter"]

    cache_test(cached_response, cache)
