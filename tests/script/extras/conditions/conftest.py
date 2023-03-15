import pytest

from dff.script import Actor
from dff.script.extras.conditions.dataset import Dataset
from dff.utils.testing.toy_script import TOY_SCRIPT

from tests.test_utils import get_path_from_tests_to_current_dir


@pytest.fixture(scope="session")
def testing_actor():
    actor = Actor(
        TOY_SCRIPT, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node")
    )
    yield actor


@pytest.fixture(scope="session")
def testing_dataset():
    yield Dataset.parse_yaml(f"examples/{get_path_from_tests_to_current_dir(__file__)}/data/example.yaml")


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
