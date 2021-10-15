# %%
import functools

from dff.core import Actor, Context
from dff.core.types import ActorStage


class TurnCache:
    def __init__(self, actor: Actor) -> Actor:
        self.wrappers = []
        actor.handlers[ActorStage.CREATE_RESPONSE] = actor.handlers.get(ActorStage.CREATE_RESPONSE, []) + [
            self.clear_cache_handler
        ]

    def clear_cache_handler(self, ctx: Context, actor: Actor, *args, **kwargs):
        [wrapper.cache_clear() for wrapper in self.wrappers]

    def cache(self, func):
        @functools.cache
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        self.wrappers += [wrapper]
        return wrapper

    def lru_cache(self, func=None, maxsize=128, typed=False):
        def decorator(func=func):
            @functools.lru_cache(maxsize=maxsize, typed=typed)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            self.wrappers += [wrapper]
            return wrapper

        return decorator

