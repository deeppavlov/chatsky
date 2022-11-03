import pytest

from df_extended_conditions.models import HFAPIModel, AsyncHFAPIModel


@pytest.fixture(scope="session")
def testing_model(hf_api_key, hf_model_name):
    yield HFAPIModel(model=hf_model_name, api_key=hf_api_key, namespace_key="hf_api_model")


@pytest.fixture(scope="session")
def testing_async_model(hf_api_key, hf_model_name):
    yield AsyncHFAPIModel(model=hf_model_name, api_key=hf_api_key, namespace_key="hf_api_async")


def test_predict(testing_model: HFAPIModel):
    print(testing_model.api_key, "- api key", sep=" ")
    result = testing_model.predict("we are looking for x.")
    assert isinstance(result, dict)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_async_predict(testing_async_model: AsyncHFAPIModel):
    result = await testing_async_model.predict("we are looking for x.")
    assert isinstance(result, dict)
    assert len(result) > 0
