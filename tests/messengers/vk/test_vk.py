import pytest
import requests
import json
import pathlib
from dff.script import Message
from dff.script.core.message import Document, Image
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
        attachment_list = []
        print("Attachment_list",  message.attachments)
        if message.attachments is not None:
            attachment_list = []
            for attachment in message.attachments:
                print("Attachment:",  attachment)
                # add id to each attachment that is being generated in upload_attachment method
                if isinstance(attachment, Image):
                    attachment_list.append(
                        {"type": "photo", "source": attachment.source}
                    )
                elif isinstance(attachment, Document):
                    attachment_list.append(
                        {"type": "doc", "source": attachment.source}
                    )
        return await iface.bot.send_message(message.text, 42, attachment_list)
    
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
        received_message = Message.model_validate_json(data["received_message"])

        parsed_messages = await patch_interface._request()

        for parsed_message in parsed_messages:
            assert parsed_message == received_message

@pytest.mark.asyncio
async def test_outgoing(patch_interface):
    with open(pathlib.Path(__file__).parent / "test_cases.json") as f:
        incoming_data = json.load(f)["outgoing"]

    for test_case, data in incoming_data.items():
        message_to_send = Message.model_validate_json(data["message"])
        trace = await patch_interface._respond(message_to_send)
        print("Trace:", trace)
        assert trace == data["methods_called"][0]
