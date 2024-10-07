from asyncio import gather
from typing import Any, Awaitable, List


async def launch_coroutines(coroutines: List[Awaitable], is_async: bool) -> List[Any]:
    return await gather(*coroutines) if is_async else [await coroutine for coroutine in coroutines]
