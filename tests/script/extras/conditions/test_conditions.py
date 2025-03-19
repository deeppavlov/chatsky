import pytest
from chatsky import Context, Message
from chatsky.conditions.ml import HasLabel, HasMatch
from chatsky.ml.models.base_model import ExtrasBaseAPIModel
from chatsky.core.node_label import AbsoluteNodeLabel
from chatsky.core.script import Node


class DummyModel(ExtrasBaseAPIModel):
    def __init__(self, model_id=None):
        self.model_id = model_id

    def predict(self, text):
        return {"label_a": 0.1, "label_b": 0.9}

    def __call__(self, text):
        pass

class MockPipeline:
    def __init__(self, mock_model):
        self.models = {
            "test_model": DummyModel(),
        }


@pytest.fixture
def pipeline(mock_model):
    return MockPipeline(mock_model)

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


@pytest.mark.parametrize(
    ["input"],
    [
        ("label_a",),
        ("label_b",),
    ],
)
def test_conditions(input, context, pipeline):
    # ctx = Context(framework_states={LABEL_KEY: {"model_a": {"a": 1, "b": 1}, "model_b": {"b": 1, "c": 1}}})
    ctx = Context().pipeline
    ctx.add_request(Message(text="idk something"))
    # model = DummyModel(model_id="model_a")
    assert HasLabel(label=input, model_name="test_model")(ctx, pipeline) is False
    assert HasLabel(label=input, model_name="test_model")(ctx, pipeline) is True
    # assert has_cls_label(input, model, namespace="model_a")(ctx, pipeline) is True
    # assert has_cls_label(input, model, threshold=1.1)(ctx, pipeline) is False
    # ctx2 = Context()
    # assert has_cls_label(input, model)(ctx2, pipeline) is False


# @pytest.mark.parametrize(["input"], [(1,), (3.3,), ({"a", "b"},)])
# def test_conds_invalid(input, testing_pipeline):
#     with pytest.raises(NotImplementedError):
#         model = DummyModel(model_id="model_a")
#         _ = has_cls_label(model, input)(Context(), testing_pipeline)


# since the standart model is no longer exist (because we do not support local models) mock-model should be created)
# @pytest.mark.parametrize(
#     ["_input", "last_request", "thresh"],
#     [
#         ({"positive_examples": ["like sweets", "like candy"], "negative_examples": ["other stuff"]}, "sweets", 0.7),
#         (
#             {
#                 "positive_examples": ["good stuff", "brilliant stuff", "excellent stuff"],
#                 "negative_examples": ["negative example"],
#             },
#             "excellent, brilliant",
#             0.5,
#         ),
#     ],
# )
# def test_has_match(_input: dict, testing_pipeline, thresh, standard_model, last_request):
#     ctx = Context()
#     ctx.add_request(Message(text=last_request))
#     # Per default, we assume that the model has already been fit.
#     # For this test case we fit it manually.
#     collection = Dataset(
#         items=[DatasetItem.model_validate({"label": key, "samples": values}) for key, values in _input.items()]
#     )
#     standard_model.fit(collection)
#     result = has_match(standard_model, threshold=thresh, **_input)(ctx, testing_pipeline)
#     assert result
