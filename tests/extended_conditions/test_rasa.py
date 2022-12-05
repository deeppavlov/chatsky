import os
import pytest

from dff.script.logic.extended_conditions.models.remote_api.rasa_model import RasaModel, AsyncRasaModel, rasa_available
from tests.db_connector.test_dbs import ping_localhost

RASA_ACTIVE = ping_localhost(5005)


@pytest.fixture(scope="session")
def testing_model():
    rasa_url, api_key = os.getenv("RASA_URL"), os.getenv("RASA_API_KEY")
    if rasa_url and api_key:
        yield RasaModel(model=rasa_url, api_key=api_key, namespace_key="rasa")
    else:
        yield None


@pytest.fixture(scope="session")
def testing_async_model():
    rasa_url, api_key = os.getenv("RASA_URL"), os.getenv("RASA_API_KEY")
    if rasa_url and api_key:
        yield AsyncRasaModel(model=rasa_url, api_key=api_key, namespace_key="rasa_async")
    else:
        yield None


@pytest.mark.skipif(not RASA_ACTIVE, reason="RASA inactive.")
@pytest.mark.skipif(not os.getenv("RASA_URL") or not os.getenv("RASA_API_KEY"), reason="No RASA API key.")
def test_predict(testing_model: RasaModel):
    request = "Hello there"
    result = testing_model.predict(request=request)
    assert isinstance(result, dict)
    assert len(result) > 0
    assert result["greet"] > 0.9  # testing on default intents that include 'greet'


@pytest.mark.skipif(not rasa_available, reason="Async deps missing.")
@pytest.mark.skipif(not RASA_ACTIVE, reason="RASA inactive.")
@pytest.mark.skipif(not os.getenv("RASA_URL") or not os.getenv("RASA_API_KEY"), reason="No RASA API key.")
@pytest.mark.asyncio
async def test_async_predict(testing_async_model: AsyncRasaModel):
    request = "Hello there"
    result = await testing_async_model.predict(request=request)
    assert isinstance(result, dict)
    assert len(result) > 0
    assert result["greet"] > 0.9  # testing on default intents that include 'greet'
