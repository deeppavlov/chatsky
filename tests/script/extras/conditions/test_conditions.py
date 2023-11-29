import pytest
from dff.script import Context, Message
from dff.script.extras.conditions.utils import LABEL_KEY
from dff.script.extras.conditions.dataset import DatasetItem, Dataset
from dff.script.extras.conditions.conditions import has_cls_label, has_match
from dff.script.extras.conditions.models.local.cosine_matchers.sklearn import SklearnMatcher, sklearn_available


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
    assert has_cls_label(input)(ctx, testing_pipeline) is True
    assert has_cls_label(input, namespace="model_a")(ctx, testing_pipeline) is True
    assert has_cls_label(input, threshold=1.1)(ctx, testing_pipeline) is False
    ctx2 = Context()
    assert has_cls_label(input)(ctx2, testing_pipeline) is False


@pytest.mark.parametrize(["input"], [(1,), (3.3,), ({"a", "b"},)])
def test_conds_invalid(input, testing_pipeline):
    with pytest.raises(NotImplementedError):
        _ = has_cls_label(input)(Context(), testing_pipeline)


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
