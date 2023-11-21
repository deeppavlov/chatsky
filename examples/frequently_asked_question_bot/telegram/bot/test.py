import pytest
from dff.utils.testing.common import check_happy_path
from dff.messengers.telegram import TelegramMessage, TelegramUI
from dff.script import RESPONSE
from dff.script.core.message import Button

from dialog_graph import script
from run import get_pipeline
from faq_model.model import faq


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "happy_path",
    [
        (
            (TelegramMessage(text="/start"), script.script["qa_flow"]["welcome_node"][RESPONSE]),
            (
                TelegramMessage(text="Why use arch?"),
                TelegramMessage(
                    text="I found similar questions in my database:",
                    ui=TelegramUI(
                        buttons=[
                            Button(text=q, payload=q)
                            for q in ["Why would I want to use Arch?", "Why would I not want to use Arch?"]
                        ]
                    ),
                ),
            ),
            (
                TelegramMessage(callback_query="Why would I want to use Arch?"),
                TelegramMessage(text=faq["Why would I want to use Arch?"]),
            ),
            (
                TelegramMessage(callback_query="Why would I not want to use Arch?"),
                TelegramMessage(text=faq["Why would I not want to use Arch?"]),
            ),
            (
                TelegramMessage(text="What is arch linux?"),
                TelegramMessage(
                    text="I found similar questions in my database:",
                    ui=TelegramUI(buttons=[Button(text=q, payload=q) for q in ["What is Arch Linux?"]]),
                ),
            ),
            (TelegramMessage(callback_query="What is Arch Linux?"), TelegramMessage(text=faq["What is Arch Linux?"])),
            (
                TelegramMessage(text="where am I?"),
                TelegramMessage(
                    text="I don't have an answer to that question. Here's a list of questions I know an answer to:",
                    ui=TelegramUI(buttons=[Button(text=q, payload=q) for q in faq]),
                ),
            ),
            (
                TelegramMessage(callback_query="What architectures does Arch support?"),
                TelegramMessage(text=faq["What architectures does Arch support?"]),
            ),
        )
    ],
)
async def test_happy_path(happy_path):
    check_happy_path(pipeline=get_pipeline(use_cli_interface=True), happy_path=happy_path)
