import pytest
import json
from vk_dummy import VKDummy
from dff.messengers.vk import PollingVKInterface

@pytest.fixture
def patch_interface():
    iface = PollingVKInterface(token="", group_id="")
    iface.bot = VKDummy()
    return iface

# incoming_data.json {"case1": [], "case2": []}

# incoming_data.json {"case1": [incoming_http_request, parsed_dff_request], "case2": []}
with open("incoming_data.json") as f:
        incoming_data = json.load(f)

# incoming_data = map({...})
@pytest.mark.parametrize("incoming_http_request,parsed_dff_request", list(map(tuple, incoming_data.values())))
def test_data_parsing(incoming_http_request, parsed_dff_request, patched_interface):
        assert parsed_dff_request == patched_interface._request(incoming_http_request)
        

