import pytest

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    import numpy as np
except ImportError:
    pytest.skip(allow_module_level=True)

from df_extended_conditions.models.local.classifiers.sklearn import SklearnClassifier
from df_extended_conditions.models.local.cosine_matchers.sklearn import SklearnMatcher
from df_extended_conditions.dataset import Dataset


@pytest.fixture(scope="session")
def testing_classifier():
    classifier = SklearnClassifier(model=LogisticRegression(), tokenizer=TfidfVectorizer(), namespace_key="classifier")
    yield classifier


@pytest.fixture(scope="session")
def testing_model(testing_dataset):
    model = SklearnMatcher(
        model=None,
        tokenizer=TfidfVectorizer(),
        dataset=testing_dataset,
        namespace_key="model",
    )
    yield model


def test_saving(save_file: str, testing_classifier: SklearnClassifier, testing_model: SklearnMatcher):
    testing_classifier.save(save_file)
    new_classifier = SklearnClassifier.load(save_file, namespace_key="classifier")
    assert type(new_classifier.model) == type(testing_classifier.model)
    assert type(new_classifier.tokenizer) == type(testing_classifier.tokenizer)
    assert new_classifier.namespace_key == testing_classifier.namespace_key
    testing_model.save(save_file)
    new_model = SklearnMatcher.load(path=save_file, namespace_key="model")
    assert type(new_classifier.model) == type(testing_classifier.model)
    assert type(new_classifier.tokenizer) == type(testing_classifier.tokenizer)
    assert new_classifier.namespace_key == testing_classifier.namespace_key


def test_fit(testing_classifier: SklearnClassifier, testing_model: SklearnMatcher, testing_dataset: Dataset):
    tc_result = testing_classifier.fit(testing_dataset)
    ts_result = testing_model.fit(testing_dataset)
    assert tc_result == ts_result == None


def test_transform(testing_model: SklearnMatcher):
    result = testing_model.transform("one two three")
    assert isinstance(result, np.ndarray)
