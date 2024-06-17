import pytest
import requests
import json
import pathlib
from dff.script import Message
from dff.messengers.vk import PollingVKInterface, extract_vk_update
import dff.messengers.vk as dff_vk
import logging

logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def patch_interface(monkeypatch):
    
    @pytest.mark.asyncio
    async def mock_request():
        with open(pathlib.Path(__file__).parent / "test_tutorial.json") as f:
            incoming_data = json.load(f)
        
        update_list = []
        for test_case, data in incoming_data.items():
            update = data["update"]
            update_list.append(
                extract_vk_update(
                    (update)
                )
            )
        return update_list

    @pytest.mark.asyncio
    async def patched_post(request_method: str, *args, **kwargs):
        print((request_method, args, kwargs))
        if "getMessagesUploadServer" in request_method:
            return {"response": {"upload_url": "https://dummy_url"}}
        elif "save" in request_method:
            return {"response": [{"owner": "dummy", "id": "123"}]}
        elif "getLongPollServer" in request_method:
            return {"response": {"server": "dummy_url", "key": "dummy_key", "ts": "dummy_ts"}}
        else:
            return request_method
    
    @pytest.mark.asyncio
    async def mock_respond(message: Message,  *args, **kwargs):
        return await iface.bot.send_message(message.text, 42, message.attachments)
    
    monkeypatch.setattr(dff_vk, "vk_api_call", patched_post)
    iface = PollingVKInterface(token="token", group_id="")
    monkeypatch.setattr(iface, "_request", mock_request)
    monkeypatch.setattr(iface, "_respond", mock_respond)
    
    return iface


@pytest.mark.asyncio
async def test_incoming(patch_interface):
    with open(pathlib.Path(__file__).parent / "test_cases.json") as f:
        incoming_data = json.load(f)["incoming"]

    for test_case, data in incoming_data.items():
        received_message = json.loads(data["received_message"])

        parsed_messages = await patch_interface._request()
        print("Parsed messages: " + str(parsed_messages))

        for parsed_message in parsed_messages:
            print("Received message:  " + str(received_message))
            assert parsed_message.text == received_message["text"]
            assert parsed_message.commands == received_message["commands"]
            assert parsed_message.attachments == received_message["attachments"]
            assert parsed_message.annotations == received_message["annotations"]
            assert parsed_message.misc == received_message["misc"]
            assert parsed_message.original_message == received_message["original_message"]

@pytest.mark.asyncio
async def test_outgoing(patch_interface):
    with open(pathlib.Path(__file__).parent / "test_cases.json") as f:
        incoming_data = json.load(f)["outgoing"]

    for test_case, data in incoming_data.items():
        msg_scheme = json.loads(data["message"])
        message_to_send = Message(text=msg_scheme["text"], commands=msg_scheme["commands"], attachments= msg_scheme["attachments"])
        trace = await patch_interface._respond(message_to_send)
        assert trace == data["methods_called"][0]