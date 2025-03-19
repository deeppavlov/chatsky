import os
import pytest

from chatsky.ml.models.hf_api_model import (
    HFAPIModel,
    hf_api_available,
)

# class MockHFAPIModel(HFAPIModel):
#     def __init__(self, model: str, api_key: str):
#         super().__init__(model=model, api_key=api_key)

#     async def predict(self, text: str) -> dict:
#         return {"mock_false_label": 0.0, "mock_true_label": 1.0}

@pytest.fixture(scope="session")
def testing_async_model(hf_model_name):
    if os.getenv("HF_API_KEY"):
        yield HFAPIModel(model=hf_model_name, api_key=os.getenv("HF_API_KEY"))
    else:
        yield None


@pytest.mark.skipif(not hf_api_available, reason="Async deps missing.")
@pytest.mark.skipif(not os.getenv("HF_API_KEY"), reason="No HF API key")
@pytest.mark.huggingface
@pytest.mark.asyncio
async def test_async_predict(testing_async_model: HFAPIModel):
    result = await testing_async_model.predict("we are looking for x.")
    assert isinstance(result, dict)
    assert len(result) > 0
