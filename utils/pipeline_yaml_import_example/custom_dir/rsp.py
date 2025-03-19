from chatsky import BaseResponse, Context, MessageInitTypes, cnd


class ListNotExtractedSlots(BaseResponse):
    async def call(self, ctx: Context) -> MessageInitTypes:
        not_extracted_slots = [key for key in ("name", "age") if not await cnd.SlotsExtracted(f"person.{key}")(ctx)]

        return f"You did not provide {not_extracted_slots} yet."
