import pytest
import requests
import json
import pathlib
from dff.script import Message
from dff.script.core.message import Document, Image
from dff.messengers.vk.interface import PollingVKInterface, extract_vk_update
import dff.messengers.vk.interface as dff_vk
import logging

logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def patch_interface(monkeypatch):
    trace = []
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
        req = {"request_method": request_method}
        if "getMessagesUploadServer" in request_method:
            req.update(kwargs)
            trace.append(req)
            return {"response": {"upload_url": "https://dummy_upload_url"}}
        elif "upload_url" in request_method:
            # hashing bytes of the file
            req.update({"file": kwargs['file'][0][1][0]})
            trace.append(req)
            return {"file": "dummy_file"}
        elif "saveMessagesPhoto" in request_method:
            req.update(kwargs)
            trace.append(req)
            return {"response": [{"id": 1234, "owner_id": 4321, "sizes": []}]}
        elif "docs.save" in request_method:
            req.update(kwargs)
            trace.append(req)
            return {"response": {"type": "doc", "doc": {"id": 1234, "owner_id": 4321}}}
        elif "getLongPollServer" in request_method:
            req.update(kwargs)
            trace.append(req)
            return {"response": {"server": "dummy_url", "key": "dummy_key", "ts": "dummy_ts"}}
        else:
            req.update(kwargs)
            trace.append(req)
            return request_method
    
    @pytest.mark.asyncio
    async def mock_respond(message: Message,  *args, **kwargs):
        attachment_list = []
        if message.attachments is not None:
            attachment_list = []
            for attachment in message.attachments:
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
    iface.trace = trace
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
        # message_to_send = Message(text="Here is your file", attachments=[Document(source="README.md")])
        await patch_interface._respond(message_to_send)
        trace = patch_interface.trace
        with open(f'{test_case}_trace.json', 'w') as f:
            f.write(json.dumps(trace))
        assert trace == data["trace"]


@pytest.mark.asyncio
async def test_tutorials(patch_interface):
    with open(pathlib.Path(__file__).parent / "test_tutorial.json") as f:
        tutorial_data = json.loads(f)

    for tutorial, data in tutorial_data.items():
        message_to_send = Message.model_validate_json(data["message"])
        # message_to_send = Message(text="Here is your file", attachments=[Document(source="README.md")])
        await patch_interface._respond(message_to_send)
        trace = patch_interface.trace
        assert trace == data["trace"]
