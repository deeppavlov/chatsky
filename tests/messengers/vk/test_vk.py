import pytest
import requests
import json
import pathlib
from dff.script import Message
from dff.messengers.vk import PollingVKInterface, extract_vk_update
import logging

logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def patch_interface(monkeypatch):
    iface = PollingVKInterface(token="", group_id="")
    
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
    
    monkeypatch.setattr(iface, "_request", mock_request)
    
    return iface

# custom class to be the mock return value
# will override the requests.Response returned from requests.get
# def test_post(monkeypatch):
#     def dummy_post(request_method: str, *args, **kwargs):
#         print((request_method, args, kwargs))
#         if "getMessagesUploadServer" in request_method:
#             return {"response": {"upload_url": "https://dummy_url"}}
#         elif "save" in request_method:
#             return {"response": [{"owner": "dummy", "id": "123"}]}
#         elif "getLongPollServer" in request_method:
#             return {"response": {"server": "dummy_url", "key": "dummy_key", "ts": "dummy_ts"}}

#     monkeypatch.setattr(requests, "post", dummy_post)

#     iface = PollingVKInterface(token="", group_id="")
#     iface._respond(Message(text="test"))

@pytest.mark.asyncio
async def test_data_parsing(patch_interface):
    with open(pathlib.Path(__file__).parent / "test_tutorial.json") as f:
        incoming_data = json.load(f)

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
