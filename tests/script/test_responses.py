import random

from dff.script import Message
from dff.script.responses import random_choice


class TestResponses:
    def test_random_choice(self, ctx, pipeline):
        random.seed(0)

        rsp = random_choice(
            [
                Message(text="1"),
                Message(text="2"),
                Message(text="3"),
            ]
        )

        assert rsp(ctx, pipeline).text == "2"
        assert rsp(ctx, pipeline).text == "2"
        assert rsp(ctx, pipeline).text == "1"
