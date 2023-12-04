"""
Asynchronous Mixin
-----------------------

This module provides the mixin that overrides the :py:meth:`__call__` method
in all the descendants making them asynchronous.
"""
from dff.script import Context
from dff.script.extras.conditions.models.base_model import ExtrasBaseModel
from dff.script.extras.conditions.utils import LABEL_KEY


class AsyncMixin(ExtrasBaseModel):
    """
    This class overrides the :py:meth:`~__call__` method
    allowing for asynchronous calls to annotator models.
    As a result, asynchronous classes can be easily integrated
    into a :py:class:`~dff.pipeline.Pipeline` object.
    """

    async def __call__(self, ctx: Context, _):
        labels = dict()
        if ctx.last_request and ctx.last_request.text:
            labels = await self.predict(ctx.last_request.text)

        if LABEL_KEY not in ctx.framework_states:
            ctx.framework_states[LABEL_KEY] = dict()
        namespace = self.namespace_key
        ctx.framework_states[LABEL_KEY][namespace] = labels
        return ctx
