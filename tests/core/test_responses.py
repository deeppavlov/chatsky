import random

import pytest

from chatsky.core import Message
from chatsky.responses import RandomChoice


@pytest.fixture
def ctx(context_factory):
    return context_factory(forbidden_fields=("labels", "requests", "responses", "misc"))


async def test_random_choice(ctx):
    random.seed(0)

    rsp = RandomChoice(
        Message(text="1"),
        Message(text="2"),
        Message(text="3"),
    )

    assert (await rsp(ctx)).text == "2"
    assert (await rsp(ctx)).text == "2"
    assert (await rsp(ctx)).text == "1"
