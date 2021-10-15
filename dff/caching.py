# %%
import functools

from dff.core import Actor, Context
from dff.core.types import ActorStage


class OneTurnCache:
    def __init__(self):
        self.wrappers = []

    def update_actor_handlers(self, actor: Actor) -> Actor:
        handlers = actor.handlers.get(ActorStage.CONTEXT_INIT, [])
        handlers += [self.clear_cache_handler]
        actor.handlers[ActorStage.CONTEXT_INIT] = handlers
        return actor

    def clear_cache_handler(self, ctx: Context, actor: Actor, *args, **kwargs):
        [wrapper.cache_clear() for wrapper in self.wrappers]

    def cache(self, func):
        @functools.cache
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        self.wrappers += [wrapper]
        return wrapper

    def lru_cache(self, maxsize=128, typed=False):
        _maxsize = 128 if callable(maxsize) else maxsize

        def decorator(func):
            @functools.lru_cache(maxsize=_maxsize, typed=typed)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            self.wrappers += [wrapper]
            return wrapper

        return decorator(maxsize) if callable(maxsize) else decorator
