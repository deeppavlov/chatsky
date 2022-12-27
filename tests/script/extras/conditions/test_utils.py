import pytest

try:
    import unknown_package

    IMPORT_ERROR_MESSAGE = None
except ImportError as e:
    unknown_package = None
    IMPORT_ERROR_MESSAGE = e.msg


from dff.script.extras.conditions.dataset import Dataset
from tests.test_utils import get_path_from_tests_to_current_dir

path = get_path_from_tests_to_current_dir(__file__)


@pytest.mark.parametrize(
    ["file", "method_name"],
    [
        (f"examples/{path}/data/example.json", "parse_json"),
        (f"examples/{path}/data/example.jsonl", "parse_jsonl"),
        (f"examples/{path}/data/example.yaml", "parse_yaml"),
    ],
)
def test_file_parsing(file, method_name):
    collection: Dataset = getattr(Dataset, method_name)(file)
    assert len(collection.items) == 3
    assert len(collection.flat_items) == 10
    prev_categorical_code = -1
    for intent in collection.items.values():
        assert len(intent.samples) >= 3
        assert intent._categorical_code != prev_categorical_code
        prev_categorical_code = intent._categorical_code
