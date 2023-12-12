import pytest
from dff.utils.testing.common import check_happy_path
from dff.messengers.telegram import TelegramMessage
from dff.script import RESPONSE, Message

from dialog_graph.script import script
from run import get_pipeline


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "happy_path",
    [
        (
            (TelegramMessage(text="/start"), script["chitchat_flow"]["init_chitchat"][RESPONSE]),
            (TelegramMessage(text="I need to make an order"), script["form_flow"]["ask_item"][RESPONSE]),
            (TelegramMessage(text="abort"), script["chitchat_flow"]["init_chitchat"][RESPONSE]),
            (TelegramMessage(text="I need to make an order"), script["form_flow"]["ask_item"][RESPONSE]),
            (TelegramMessage(text="'Pale Fire', 'Lolita'"), script["form_flow"]["ask_delivery"][RESPONSE]),
            (
                TelegramMessage(text="I want it delivered to my place"),
                script["form_flow"]["ask_payment_method"][RESPONSE],
            ),
            (TelegramMessage(text="abort"), script["chitchat_flow"]["init_chitchat"][RESPONSE]),
            (TelegramMessage(text="I need to make an order"), script["form_flow"]["ask_item"][RESPONSE]),
            (TelegramMessage(text="'Pale Fire', 'Lolita'"), script["form_flow"]["ask_delivery"][RESPONSE]),
            (
                TelegramMessage(text="I want it delivered to my place"),
                script["form_flow"]["ask_payment_method"][RESPONSE],
            ),
            (TelegramMessage(text="foo bar baz"), script["form_flow"]["ask_payment_method"][RESPONSE]),
            (
                TelegramMessage(text="card"),
                Message(
                    text="We registered your transaction. Requested titles are: Pale Fire, Lolita. "
                    "Delivery method: deliver. Payment method: card. "
                    "Type `abort` to cancel, type `ok` to continue."
                ),
            ),
            (TelegramMessage(text="ok"), script["chitchat_flow"]["init_chitchat"][RESPONSE]),
        )
    ],
)
async def test_happy_path(happy_path):
    check_happy_path(pipeline=get_pipeline(use_cli_interface=True), happy_path=happy_path)
