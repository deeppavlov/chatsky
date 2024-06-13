import pytest
import requests
import json
import pathlib
from dff.script import Message
from dff.messengers.vk import PollingVKInterface

@pytest.fixture
def patch_interface():
    iface = PollingVKInterface(token="", group_id="")
    # iface.bot = VKDummy()
    return iface

# custom class to be the mock return value
# will override the requests.Response returned from requests.get
def test_post(monkeypatch):
    def dummy_post(request_method: str, *args, **kwargs):
        print((request_method, args, kwargs))
        if "getMessagesUploadServer" in request_method:
            return {"response": {"upload_url": "https://dummy_url"}}
        elif "save" in request_method:
            return {"response": [{"owner": "dummy", "id": "123"}]}
        elif "getLongPollServer" in request_method:
            return {"response": {"server": "dummy_url", "key": "dummy_key", "ts": "dummy_ts"}}

    monkeypatch.setattr(requests, "post", dummy_post)

    iface = PollingVKInterface(token="", group_id="")
    iface._respond(Message(text="test"))


def test_data_parsing(patch_interface):
    with open( pathlib.Path(__file__).parent / "/test_tutorial.json") as f:
        incoming_data = json.load(f)

    for test_case, data in incoming_data.items():
        update = data["update"]
        received_message = json.loads(data["received_message"])
        expected_message = Message(
            text=received_message["text"],
            commands=received_message["commands"],
            attachments=received_message["attachments"],
            annotations=received_message["annotations"],
            misc=received_message["misc"],
            original_message=received_message["original_message"]
        )

        parsed_message = patch_interface._request(update)

        assert parsed_message == expected_message

# with open("incoming_data.json") as f:
#     incoming_data = json.load(f)
        
# for i in incoming_data:
#     incoming_data[i][1] = Message(text=incoming_data[i][1]["text"])

# @pytest.mark.parametrize("incoming_http_request,parsed_dff_request", list(map(tuple, incoming_data.values())))
# def test_data_parsing(incoming_http_request, parsed_dff_request, patched_interface):
#         assert parsed_dff_request == patched_interface._request(incoming_http_request)
