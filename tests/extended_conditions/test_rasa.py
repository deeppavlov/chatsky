import os

import requests
import pytest

from dff.script.logic.extended_conditions.models import RasaModel, AsyncRasaModel

RASA_URL = os.getenv("RASA_URL", "http://localhost:5005")
if RASA_URL is None or isinstance(RASA_URL, str) and requests.get(RASA_URL).status_code != 200:
    pytest.skip(allow_module_level=True)


@pytest.fixture(scope="session")
def testing_model(rasa_url, rasa_api_key):
    yield RasaModel(model=RASA_URL, api_key=rasa_api_key, namespace_key="rasa")


@pytest.fixture(scope="session")
def testing_async_model(rasa_url):
    yield AsyncRasaModel(model=RASA_URL, namespace_key="rasa_async")


def test_predict(testing_model: RasaModel):
    request = "Hello there"
    result = testing_model.predict(request=request)
    assert isinstance(result, dict)
    assert len(result) > 0
    assert result["greet"] > 0.9  # testing on default intents that include 'greet'


@pytest.mark.asyncio
async def test_async_predict(testing_async_model: AsyncRasaModel):
    request = "Hello there"
    result = await testing_async_model.predict(request=request)
    assert isinstance(result, dict)
    assert len(result) > 0
    assert result["greet"] > 0.9  # testing on default intents that include 'greet'
