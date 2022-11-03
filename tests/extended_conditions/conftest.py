import os
import sys

import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from dff.script.logic.extended_conditions.models.local.cosine_matchers.sklearn import SklearnMatcher
from dff.script.logic.extended_conditions.dataset import Dataset

sys.path.insert(0, os.path.pardir)


@pytest.fixture(scope="session")
def testing_actor():
    from examples.base_example import actor

    yield actor


@pytest.fixture(scope="session")
def testing_dataset():
    yield Dataset.parse_yaml("./examples/data/example.yaml")


@pytest.fixture(scope="session")
def standard_model(testing_dataset):
    yield SklearnMatcher(tokenizer=TfidfVectorizer(stop_words=None), dataset=testing_dataset)


@pytest.fixture(scope="session")
def hf_api_key():
    yield os.getenv("HF_API_KEY", "")


@pytest.fixture(scope="session")
def gdf_json(tmpdir_factory):
    json_file = tmpdir_factory.mktemp("gdf").join("service_account.json")
    contents = os.getenv("GDF_ACCOUNT_JSON")
    json_file.write(contents)
    yield str(json_file)


@pytest.fixture(scope="session")
def hf_model_name():
    yield "obsei-ai/sell-buy-intent-classifier-bert-mini"


@pytest.fixture(scope="session")
def rasa_url():
    yield os.getenv("RASA_URL") or ""


@pytest.fixture(scope="session")
def rasa_api_key():
    yield os.getenv("RASA_API_KEY") or ""


@pytest.fixture(scope="session")
def save_file(tmpdir_factory):
    file_name = tmpdir_factory.mktemp("testdir").join("testfile")
    return str(file_name)
