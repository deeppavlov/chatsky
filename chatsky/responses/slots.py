"""
Response
---------------------------
Slot-related Chatsky responses.
"""

from chatsky.core import Context, Message, BaseResponse
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
    template: Message

    def __init__(self, template: MessageInitTypes):
        super().__init__(template=template)

    async def func(self, ctx: Context) -> MessageInitTypes:
        message = self.template.model_copy()
        if message.text is not None:
            message.text = ctx.framework_data.slot_manager.fill_template(message.text)
        return message
