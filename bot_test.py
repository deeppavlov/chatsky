import asyncio
from dff.messengers import vk
from dff.pipeline import Pipeline

from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    HAPPY_PATH,
    TOY_SCRIPT,
    TOY_SCRIPT_ARGS,
)

KEY = "vk1.a.BwQyndaC87dkYdmZQt9TCGuRx5VRh1_ZyvGy5Twxl35-u8euOrjHPU4YNh7Re7C-S8Am8zRyuexBatnFLksrfzCPG3kYXNmQ0Gm2Wld1Cx3b8VPAnW0M0agaDDboDBm5iYZdMJutpTqAqCyWlAaZPdEcKLdgSyqRSLO2cLac7MwTtOzN4jTtd8WJUoHOd3Ts0Af_KyefrG-NEzP9BbMHYA"
GROUP_ID = "224377718"

interface = vk.PollingVKInterface(KEY, GROUP_ID)

pipeline = Pipeline.from_script(
    *TOY_SCRIPT_ARGS,
    messenger_interface=interface,
    # The interface can be passed as a pipeline argument.
)

async def main():
    await interface.connect(pipeline)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())