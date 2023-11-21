"""
Script
--------
This module defines the bot script.
"""
from dff.script import RESPONSE, TRANSITIONS, LOCAL, PRE_TRANSITIONS_PROCESSING, PRE_RESPONSE_PROCESSING
from dff.script import Message
from dff.script import conditions as cnd
from dff.script import labels as lbl

from . import conditions as loc_cnd
from . import response as loc_rsp
from . import processing as loc_prc


script = {
    "general_flow": {
        LOCAL: {
            TRANSITIONS: {
                ("form_flow", "ask_item", 1.0): cnd.any(
                    [loc_cnd.has_intent(["purchase"]), cnd.regexp(r"\border\b|\bpurchase\b")]
                ),
                ("chitchat_flow", "init_chitchat", 0.8): cnd.true(),
            },
            PRE_TRANSITIONS_PROCESSING: {"1": loc_prc.extract_intents()},
        },
        "start_node": {
            RESPONSE: Message(text=""),
        },
        "fallback_node": {
            RESPONSE: Message(text="Cannot recognize your query. Type 'ok' to continue."),
        },
    },
    "chitchat_flow": {
        LOCAL: {
            TRANSITIONS: {
                ("form_flow", "ask_item", 1.0): cnd.any(
                    [loc_cnd.has_intent(["purchase"]), cnd.regexp(r"\border\b|\bpurchase\b")]
                ),
            },
            PRE_TRANSITIONS_PROCESSING: {"1": loc_prc.clear_intents(), "2": loc_prc.extract_intents()},
        },
        "init_chitchat": {
            RESPONSE: Message(text="'Book Lovers Paradise' welcomes you! Ask us anything you would like to know."),
            TRANSITIONS: {("chitchat_flow", "chitchat", 0.8): cnd.true()},
            PRE_TRANSITIONS_PROCESSING: {"2": loc_prc.clear_slots()},
        },
        "chitchat": {
            PRE_RESPONSE_PROCESSING: {"1": loc_prc.generate_response()},
            TRANSITIONS: {lbl.repeat(0.8): cnd.true()},  # repeat unless conditions for moving forward are met
            RESPONSE: loc_rsp.choose_response,
        },
    },
    "form_flow": {
        LOCAL: {
            TRANSITIONS: {
                ("chitchat_flow", "init_chitchat", 1.2): cnd.any(
                    [cnd.regexp(r"\bcancel\b|\babort\b"), loc_cnd.has_intent(["no"])]
                ),
            }
        },
        "ask_item": {
            RESPONSE: Message(
                text="Which books would you like to order? Please, separate the titles by commas (type 'abort' to cancel)."
            ),
            PRE_TRANSITIONS_PROCESSING: {"1": loc_prc.extract_item()},
            TRANSITIONS: {("form_flow", "ask_delivery"): loc_cnd.slots_filled(["items"]), lbl.repeat(0.8): cnd.true()},
        },
        "ask_delivery": {
            RESPONSE: Message(
                text="Which delivery method would you like to use? We currently offer pickup or home delivery."
            ),
            PRE_TRANSITIONS_PROCESSING: {"1": loc_prc.extract_delivery()},
            TRANSITIONS: {
                ("form_flow", "ask_payment_method"): loc_cnd.slots_filled(["delivery"]),
                lbl.repeat(0.8): cnd.true(),  # repeat unless conditions for moving forward are met
            },
        },
        "ask_payment_method": {
            RESPONSE: Message(text="Please, enter the payment method you would like to use: cash or credit card."),
            PRE_TRANSITIONS_PROCESSING: {"1": loc_prc.extract_payment_method()},
            TRANSITIONS: {
                ("form_flow", "success"): loc_cnd.slots_filled(["payment_method"]),
                lbl.repeat(0.8): cnd.true(),  # repeat unless conditions for moving forward are met
            },
        },
        "success": {
            RESPONSE: loc_rsp.confirm,
            TRANSITIONS: {("chitchat_flow", "init_chitchat"): cnd.true()},
        },
    },
}
