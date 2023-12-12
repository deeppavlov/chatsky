import pytest
from dff.utils.testing.common import check_happy_path
from dff.script import Message
from dff.pipeline import Pipeline

from .dialog_graph import script
from .pipeline_services import pre_services
from .dialog_graph.responses import get_bot_answer, get_fallback_answer, FIRST_MESSAGE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "happy_path",
    [
        (
            (
                Message(),
                FIRST_MESSAGE,
            ),
            (
                Message(text="Why use Deeppavlov?"),
                get_bot_answer("Why would I want to use Deeppavlov?", "en"),
            ),
            (
                Message(text="What is deeppavlov?"),
                get_bot_answer("What is Deeppavlov?", "en"),
            ),
            (
                Message(text="where am I?"),
                get_fallback_answer("en"),
            ),
        )
    ],
)
async def test_happy_path(happy_path):
    check_happy_path(
        pipeline=Pipeline.from_script(**script.pipeline_kwargs, pre_services=pre_services.services),
        happy_path=happy_path,
    )
