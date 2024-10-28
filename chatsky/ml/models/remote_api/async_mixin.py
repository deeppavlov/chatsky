"""
Asynchronous Mixin
-----------------------

This module provides the mixin that overrides the :py:meth:`__call__` method
in all the descendants making them asynchronous.
"""
from chatsky import Context
from chatsky.ml.models.base_model import ExtrasBaseAPIModel


class AsyncMixin(ExtrasBaseAPIModel):
    """
    This class overrides the :py:meth:`~__call__` method
    allowing for asynchronous calls to annotator models.
    As a result, asynchronous classes can be easily integrated
    into a :py:class:`~chatsky.pipeline.Pipeline` object.
    """

    async def __call__(self, ctx: Context, _):
        labels = dict()
        if ctx.last_request and ctx.last_request.text:
            labels = await self.predict(ctx.last_request.text)

        ctx.framework_data.models_labels[self.model_id] = labels
        return ctx
