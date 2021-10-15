from dff.core import Context, Actor
from dff.labels import repeat
from dff.conditions import true
from dff.core.keywords import RESPONSE, TRANSITIONS
from dff.caching import OneTurnCache


def cache_test(cached_response, cache):

    ctx = Context()
    ctx.add_label(["flow", "node1"])

    def response(ctx: Context, actor: Actor, *args, **kwargs):
        if ctx.validation:
            return ""
        return f"{cached_response(1)}-{cached_response(1)}-{cached_response(1)}-{cached_response(2)}"

    plot = {"flow": {"node1": {TRANSITIONS: {repeat(): true()}, RESPONSE: response}}}
    actor = Actor(plot=plot, start_label=("flow", "node1"), fallback_label=("flow", "node1"))
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
    def cached_response(arg):
        external_data["counter"] += 1
        return external_data["counter"]

    cache_test(cached_response, cache)
    cache = OneTurnCache()

    external_data = {"counter": 0}

    @cache.lru_cache(maxsize=32)
    def cached_response(arg):
        external_data["counter"] += 1
        return external_data["counter"]

    cache_test(cached_response, cache)
