import os
import pytest

from dff.script.extras.conditions.models.remote_api.hf_api_model import (
    HFAPIModel,
    AsyncHFAPIModel,
    hf_api_available,
)


@pytest.fixture(scope="session")
def testing_model(hf_model_name):
    if os.getenv("HF_API_KEY"):
        yield HFAPIModel(model=hf_model_name, api_key=os.getenv("HF_API_KEY"), namespace_key="hf_api_model")
    else:
        yield None


@pytest.fixture(scope="session")
def testing_async_model(hf_model_name):
    if os.getenv("HF_API_KEY"):
        yield AsyncHFAPIModel(model=hf_model_name, api_key=os.getenv("HF_API_KEY"), namespace_key="hf_api_async")
    else:
        yield None


@pytest.mark.skipif(not os.getenv("HF_API_KEY"), reason="No HF API key")
@pytest.mark.huggingface
def test_predict(testing_model: HFAPIModel):
    result = testing_model.predict("we are looking for x.")
    assert isinstance(result, dict)
    assert len(result) > 0


@pytest.mark.skipif(not hf_api_available, reason="Async deps missing.")
@pytest.mark.skipif(not os.getenv("HF_API_KEY"), reason="No HF API key")
@pytest.mark.huggingface
@pytest.mark.asyncio
async def test_async_predict(testing_async_model: AsyncHFAPIModel):
    result = await testing_async_model.predict("we are looking for x.")
    assert isinstance(result, dict)
    assert len(result) > 0
