import pytest

from dff.script.extras.conditions.models.local.cosine_matchers.gensim import GensimMatcher, gensim_available
from dff.script.extras.conditions.models.local.cosine_matchers.cosine_matcher_mixin import numpy_available
from dff.script.extras.conditions.dataset import Dataset

if not gensim_available or not numpy_available:
    pytest.skip(allow_module_level=True, reason="`Gensim` package missing.")

import numpy as np
import gensim
import gensim.downloader as api


@pytest.fixture(scope="session")
def testing_model(testing_dataset):
    wv = api.load("glove-wiki-gigaword-50")
    model = gensim.models.word2vec.Word2Vec()
    model.wv = wv
    model = GensimMatcher(model=model, dataset=testing_dataset, namespace_key="gensim", min_count=1)
    yield model


def test_transform(testing_model: GensimMatcher):
    result = testing_model.transform("one two three")
    assert isinstance(result, np.ndarray)


def test_fit(testing_model: GensimMatcher, testing_dataset: Dataset):
    testing_model.fit(testing_dataset, min_count=1)
    assert testing_model


def test_saving(save_file: str, testing_model: GensimMatcher):
    testing_model.save(save_file)
    new_testing_model = GensimMatcher.load(save_file, "gensim")
    assert new_testing_model
