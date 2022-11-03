from dff.core.engine.core import Context, Actor

from ..base_model import BaseModel
from ...utils import LABEL_KEY


class AsyncMixin(BaseModel):
    async def __call__(self, ctx: Context, actor: Actor):
        labels = dict()
        if ctx.last_request is not None:
            labels = await self.predict(ctx.last_request)

        if LABEL_KEY not in ctx.framework_states:
            ctx.framework_states[LABEL_KEY] = dict()
        namespace = self.namespace_key
        ctx.framework_states[LABEL_KEY][namespace] = labels
        return ctx
