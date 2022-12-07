from pathlib import Path

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from dff.core.engine.core import Actor
from dff.script.logic.extended_conditions.models.local.cosine_matchers.sklearn import SklearnMatcher
from dff.script.logic.extended_conditions.dataset import Dataset
from dff.utils.testing.toy_script import TOY_SCRIPT

import tests.utils as utils


@pytest.fixture(scope="session")
def testing_actor():
    actor = Actor(
        TOY_SCRIPT, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node")
    )
    yield actor


@pytest.fixture(scope="session")
def testing_dataset():
    yield Dataset.parse_yaml(
        Path(__file__).parent.parent.parent
        / f"examples/{utils.get_path_from_tests_to_current_dir(__file__)}/data/example.yaml"
    )


@pytest.fixture(scope="session")
def standard_model(testing_dataset):
    yield SklearnMatcher(tokenizer=TfidfVectorizer(stop_words=None), dataset=testing_dataset)


@pytest.fixture(scope="session")
def hf_model_name():
    yield "obsei-ai/sell-buy-intent-classifier-bert-mini"


@pytest.fixture(scope="session")
def save_dir(tmpdir_factory):
    dir_name = tmpdir_factory.mktemp("testdir")
    yield dir_name


@pytest.fixture(scope="session")
def save_file(save_dir):
    file_name = save_dir.join("testfile")
    return str(file_name)
