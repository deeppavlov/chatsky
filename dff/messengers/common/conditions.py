from dff.pipeline import Pipeline
from dff.script import Context
from dff.script.core.message import CallbackQuery


def has_callback_query(expected: str):
    def condition(ctx: Context, _: Pipeline, *__, **___) -> bool:  # pragma: no cover
        last_request = ctx.last_request
        if last_request is None or last_request.attachments is None or len(last_request.attachments) == 0:
            return False
        callback_query = next(
            (attachment for attachment in last_request.attachments if isinstance(attachment, CallbackQuery)), None
        )
        if callback_query is None:
            return False
        return callback_query.query_string == expected

    return condition
