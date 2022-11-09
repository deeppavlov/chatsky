import pytest

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch
    import numpy as np
except ImportError:
    pytest.skip(allow_module_level=True)

from dff.script.logic.extended_conditions.models.local.classifiers.huggingface import HFClassifier
from dff.script.logic.extended_conditions.models.local.cosine_matchers.huggingface import HFMatcher


@pytest.fixture(scope="session")
def testing_model(hf_model_name):
    yield AutoModelForSequenceClassification.from_pretrained(hf_model_name)


@pytest.fixture(scope="session")
def testing_tokenizer(hf_model_name):
    yield AutoTokenizer.from_pretrained(hf_model_name)


@pytest.fixture(scope="session")
def testing_classifier(testing_model, testing_tokenizer):
    yield HFClassifier(
        model=testing_model, tokenizer=testing_tokenizer, device=torch.device("cpu"), namespace_key="HFclassifier"
    )


@pytest.fixture(scope="session")
def hf_matcher(testing_model, testing_tokenizer):
    yield HFMatcher(
        model=testing_model, tokenizer=testing_tokenizer, device=torch.device("cpu"), namespace_key="HFmodel"
    )


def test_saving(save_file: str, testing_classifier: HFClassifier, hf_matcher: HFMatcher):
    testing_classifier.save(path=save_file)
    testing_classifier = HFClassifier.load(save_file, namespace_key="HFclassifier")
    assert testing_classifier
    hf_matcher.save(path=save_file)
    hf_matcher = HFMatcher.load(save_file, namespace_key="HFmodel")
    assert hf_matcher


def test_predict(testing_classifier: HFClassifier):
    result = testing_classifier.predict("We are looking for x.")
    assert result
    assert isinstance(result, dict)


def test_transform(hf_matcher: HFMatcher, testing_classifier: HFClassifier):
    result_1 = hf_matcher.transform()
    assert isinstance(result_1, np.ndarray)
    result_2 = testing_classifier.transform()
    assert isinstance(result_2, np.ndarray)
