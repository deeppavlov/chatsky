import pytest
import requests
import json
from dff.script import Message
from dff.messengers.vk import PollingVKInterface

@pytest.fixture
def patch_interface():
    iface = PollingVKInterface(token="", group_id="")
    # iface.bot = VKDummy()
    return iface

# custom class to be the mock return value
# will override the requests.Response returned from requests.get
class MockResponse:
    # mock json() method always returns a specific testing dictionary
    @staticmethod
    def json():
        return {"mock_key": "mock_response"}


def test_post(monkeypatch):
    # Any arguments may be passed and mock_get() will always return our
    # mocked object, which only has the .json() method.
    def dummy_post(request_method: str, *args, **kwargs):
        """Function for logging POST requests that will override original `requests.post` method.
        Will return dummy objects for requests that require response.

        Args:
            request (_str_): method to request
            data (_dict_): data to post
        """
        print((request_method, args, kwargs))
        if "getMessagesUploadServer" in request_method:
            return {"response": {"upload_url": "https://dummy_url"}}
        elif "save" in request_method:
            return {"response": [{"owner": "dummy", "id": "123"}]}
        elif "getLongPollServer" in request_method:
            return {"response": {"server": "dummy_url", "key": "dummy_key", "ts": "dummy_ts"}}

    monkeypatch.setattr(requests, "post", dummy_post)

    # app.get_json, which contains requests.get, uses the monkeypatch
    # result = app.get_json("https://fakeurl")
    # assert result["mock_key"] == "mock_response"

    iface = PollingVKInterface(token="", group_id="")
    iface._respond(Message(text="test"))


# with open("incoming_data.json") as f:
#     incoming_data = json.load(f)
        
# for i in incoming_data:
#     incoming_data[i][1] = Message(text=incoming_data[i][1]["text"])

# @pytest.mark.parametrize("incoming_http_request,parsed_dff_request", list(map(tuple, incoming_data.values())))
# def test_data_parsing(incoming_http_request, parsed_dff_request, patched_interface):
#         assert parsed_dff_request == patched_interface._request(incoming_http_request)
