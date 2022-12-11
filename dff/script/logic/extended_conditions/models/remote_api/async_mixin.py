"""
Async Mixin
------------

This module provides a mixin that overrides the :py:meth:`__call__` method
in all the descendants making them asynchronous.
"""
from dff.core.engine.core import Context, Actor

from ..base_model import BaseModel
from ...utils import LABEL_KEY


class AsyncMixin(BaseModel):
    """
    This class allows calls to an annotator to be asynchronous.
    Thanks to this, asynchronous classes can be easily integrated
    into a `Pipeline` object.

    """
    async def __call__(self, ctx: Context, actor: Actor):
        labels = dict()
        if ctx.last_request is not None:
            labels = await self.predict(ctx.last_request)

        if LABEL_KEY not in ctx.framework_states:
            ctx.framework_states[LABEL_KEY] = dict()
        namespace = self.namespace_key
        ctx.framework_states[LABEL_KEY][namespace] = labels
        return ctx
