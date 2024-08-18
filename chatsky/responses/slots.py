"""
Response
---------------------------
Slot-related Chatsky responses.
"""

from typing import Union, Literal
import logging

from chatsky.core import Context, Message, BaseResponse
from chatsky.core.script_function import AnyResponse
from chatsky.core.message import MessageInitTypes


logger = logging.getLogger(__name__)


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
    on_exception: Literal["keep_template", "return_none"] = "return_none"

    def __init__(self,
                 template: Union[MessageInitTypes, BaseResponse],
                 on_exception: Literal["keep_template", "return_none"] = "return_none"):
        super().__init__(template=template, on_exception=on_exception)

    async def func(self, ctx: Context) -> MessageInitTypes:
        result = await self.template.wrapped_call(ctx)
        if not isinstance(result, Message):
            raise ValueError("Cannot fill template: response did not return Message.")

        if result.text is not None:
            filled = ctx.framework_data.slot_manager.fill_template(result.text)
            if isinstance(filled, str):
                result.text = filled
                return result
            else:
                if self.on_exception == "return_none":
                    return Message()
                else:
                    return result
        else:
            logger.warning(f"`template` of `FilledTemplate` returned `Message` without `text`: {result}.")
            return result
