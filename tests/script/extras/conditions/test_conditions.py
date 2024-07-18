import pytest
from chatsky.script import Context, Message
from chatsky.script.conditions.llm_conditions.utils import LABEL_KEY
from chatsky.script.conditions.llm_conditions.dataset import DatasetItem, Dataset
from chatsky.script.conditions.llm_conditions.conditions import has_cls_label, has_match
from chatsky.script.conditions.llm_conditions.models.local.cosine_matchers.sklearn import SklearnMatcher, sklearn_available
from chatsky.script.conditions.llm_conditions.models.base_model import ExtrasBaseModel


class DummyModel(ExtrasBaseModel):
    def __init__(self, model_id=None):
        self.model_id = model_id

    def predict(self, text):
        return {'label_a': 0.1, 'label_b': 0.9}

    def __call__(self, text):
        pass


@pytest.fixture(scope="session")
def standard_model(testing_dataset):
    from sklearn.feature_extraction.text import TfidfVectorizer

    yield SklearnMatcher(tokenizer=TfidfVectorizer(stop_words=None), dataset=testing_dataset)


@pytest.mark.parametrize(
    ["input"],
    [
        ("a",),
        (DatasetItem(label="a", samples=["a"]),),
        (["a", "b"],),
        ([DatasetItem(label="a", samples=["a"]), DatasetItem(label="b", samples=["b"])],),
    ],
)
def test_conditions(input, testing_pipeline):
    ctx = Context(framework_states={LABEL_KEY: {"model_a": {"a": 1, "b": 1}, "model_b": {"b": 1, "c": 1}}})
    model = DummyModel(model_id="model_a")
    assert has_cls_label(model, input)(ctx, testing_pipeline) is True
    assert has_cls_label(model, input, namespace="model_a")(ctx, testing_pipeline) is True
    assert has_cls_label(model, input, threshold=1.1)(ctx, testing_pipeline) is False
    ctx2 = Context()
    assert has_cls_label(model, input)(ctx2, testing_pipeline) is False


@pytest.mark.parametrize(["input"], [(1,), (3.3,), ({"a", "b"},)])
def test_conds_invalid(input, testing_pipeline):
    with pytest.raises(NotImplementedError):
        model = DummyModel(model_id="model_a")
        _ = has_cls_label(model, input)(Context(), testing_pipeline)


@pytest.mark.skipif(not sklearn_available, reason="Sklearn package missing.")
@pytest.mark.parametrize(
    ["_input", "last_request", "thresh"],
    [
        ({"positive_examples": ["like sweets", "like candy"], "negative_examples": ["other stuff"]}, "sweets", 0.7),
        (
            {
                "positive_examples": ["good stuff", "brilliant stuff", "excellent stuff"],
                "negative_examples": ["negative example"],
            },
            "excellent, brilliant",
            0.5,
        ),
    ],
)
def test_has_match(_input: dict, testing_pipeline, thresh, standard_model, last_request):
    ctx = Context()
    ctx.add_request(Message(text=last_request))
    # Per default, we assume that the model has already been fit.
    # For this test case we fit it manually.
    collection = Dataset(
        items=[DatasetItem.model_validate({"label": key, "samples": values}) for key, values in _input.items()]
    )
    standard_model.fit(collection)
    result = has_match(standard_model, threshold=thresh, **_input)(ctx, testing_pipeline)
    assert result
