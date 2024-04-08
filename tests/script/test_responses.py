import random

import pytest

from dff.pipeline import Pipeline
from dff.script import Message, Context
from dff.script.responses import random_choice


class TestResponses:
    pipeline = Pipeline.from_script(script={"flow": {"node": {}}}, start_label=("flow", "node"))

    @pytest.fixture
    def ctx(self):
        yield Context()

    def test_random_choice(self, ctx):
        random.seed(0)

        rsp = random_choice(
            [
                Message(text="1"),
                Message(text="2"),
                Message(text="3"),
            ]
        )

        assert rsp(ctx, self.pipeline).text == "2"
        assert rsp(ctx, self.pipeline).text == "2"
        assert rsp(ctx, self.pipeline).text == "1"
