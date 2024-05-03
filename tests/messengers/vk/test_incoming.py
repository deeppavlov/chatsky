import pytest
import json
from dff.script import Message
from vk_dummy import VKDummy
from dff.messengers.vk import PollingVKInterface

@pytest.fixture
def patch_interface():
    iface = PollingVKInterface(token="", group_id="")
    iface.bot = VKDummy()
    return iface

with open("incoming_data.json") as f:
    incoming_data = json.load(f)
        
for i in incoming_data:
    incoming_data[i][1] = Message(text=incoming_data[i][1]["text"])

@pytest.mark.parametrize("incoming_http_request,parsed_dff_request", list(map(tuple, incoming_data.values())))
def test_data_parsing(incoming_http_request, parsed_dff_request, patched_interface):
        assert parsed_dff_request == patched_interface._request(incoming_http_request)
