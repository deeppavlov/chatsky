import pytest
from chatsky import Context, Message
from chatsky.conditions.ml import HasLabel, HasMatch
from chatsky.ml.models.base_model import ExtrasBaseAPIModel
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.script import Node

predict_counter = 0


class DummyModel(ExtrasBaseAPIModel):
    def __init__(self, model_id=None):
        self.model_id = model_id

    async def predict(self, text):
        global predict_counter
        predict_counter += 1
        return {"label_a": 0.1, "label_b": 0.9}


class MockPipeline:
    def __init__(self):
        self.models = {
            "test_model": DummyModel(),
        }


@pytest.fixture
def pipeline():
    return MockPipeline()


@pytest.fixture
def context(pipeline, context_factory):
    ctx = context_factory(start_label=AbsoluteNodeLabel(flow_name="flow", node_name="node"))
    ctx.framework_data.pipeline = pipeline
    ctx.framework_data.current_node = Node()
    for i in range(1, 4):
        ctx.requests[i] = f"Request {i}"
        ctx.responses[i] = f"Response {i}"
    ctx.requests[4] = "Last request"
    ctx.current_turn_id = 4
    return ctx


async def test_conditions(context, pipeline):
    global predict_counter
    predict_counter = 0
    assert await HasLabel(label="label_a", model_name="test_model")(context) is False
    assert await HasLabel(label="label_b", model_name="test_model")(context) is True
    # TODO: check if predict was called only once
    assert predict_counter == 1


# @pytest.mark.parametrize(["input"], [(1,), (3.3,), ({"a", "b"},)])
# def test_conds_invalid(input, testing_pipeline):
#     with pytest.raises(NotImplementedError):
#         model = DummyModel(model_id="model_a")
#         _ = has_cls_label(model, input)(Context(), testing_pipeline)
