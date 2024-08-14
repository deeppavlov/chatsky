"""
Response
---------------------------
Slot-related Chatsky responses.
"""

from typing import Union

from chatsky.core import Context, Message, BaseResponse
from chatsky.core.script_function import AnyResponse
from chatsky.core.message import MessageInitTypes


class FilledTemplate(BaseResponse):
    """
    Fill template with slot values.
    The `text` attribute of the template message should be a format-string:
    e.g. "Your username is {profile.username}".

    For the example above, if ``profile.username`` slot has value "admin",
    it would return a copy of the message with the following text:
    "Your username is admin".

    :param template: Template message with a format-string text.
    """
    template: AnyResponse

    def __init__(self, template: Union[MessageInitTypes, BaseResponse]):
        super().__init__(template=template)

    async def func(self, ctx: Context) -> MessageInitTypes:
        result = self.template.wrapped_call(ctx)
        if not isinstance(result, Message):
            raise ValueError("Cannot fill template: response did not return Message.")
        if result.text is not None:
            result.text = ctx.framework_data.slot_manager.fill_template(result.text)
        return result
