import pytest

try:
    from google.cloud import dialogflow_v2
    from google.oauth2 import service_account
except ImportError:
    pytest.skip(allow_module_level=True)

from dff.script.logic.extended_conditions.models import GoogleDialogFlowModel, AsyncGoogleDialogFlowModel


@pytest.fixture(scope="session")
def testing_model(gdf_json):
    yield GoogleDialogFlowModel.from_file(filename=gdf_json, namespace_key="dialogflow")


@pytest.fixture(scope="session")
def testing_async_model(gdf_json):
    yield AsyncGoogleDialogFlowModel.from_file(filename=gdf_json, namespace_key="gdf_async")


def test_predict(testing_model: GoogleDialogFlowModel):
    test_phrase = "I would like some food"  # no matching intent in test project
    result = testing_model.predict(test_phrase)
    assert isinstance(result, dict)
    assert len(result) == 1  # should only return the fallback intent
    test_phrase_2 = "Hello there"
    result_2 = testing_model.predict(test_phrase_2)  # has a matching intent
    assert isinstance(result_2, dict)
    assert len(result_2) >= 1  # expected to return 'hello' intent


@pytest.mark.asyncio
async def test_async_predict(testing_async_model: AsyncGoogleDialogFlowModel):
    test_phrase = "I would like some food"  # no matching intent in test project
    result = await testing_async_model.predict(test_phrase)
    assert isinstance(result, dict)
    assert len(result) == 1  # should only return the fallback intent
    test_phrase_2 = "Hello there"
    result_2 = await testing_async_model.predict(test_phrase_2)  # has a matching intent
    assert isinstance(result_2, dict)
    assert len(result_2) >= 1  # expected to return 'hello' intent
