import pytest

from dff.script import Context, Message
from dff.script.extras.conditions.dataset import Dataset, pyyaml_available
from dff.script.extras.conditions.utils import LABEL_KEY
from dff.script.extras.conditions.models.remote_api.async_mixin import AsyncMixin
from tests.test_utils import get_path_from_tests_to_current_dir

path = get_path_from_tests_to_current_dir(__file__)


@pytest.mark.parametrize(
    ["file", "method_name", "skip_condition"],
    [
        (f"tutorials/{path}/data/example.json", "parse_json", None),
        (f"tutorials/{path}/data/example.jsonl", "parse_jsonl", None),
        (f"tutorials/{path}/data/example.yaml", "parse_yaml", not pyyaml_available),
    ],
)
def test_file_parsing(file, method_name, skip_condition):
    if skip_condition:
        pytest.skip(f"Skipping {file}: dependencies missing.")
    collection: Dataset = getattr(Dataset, method_name)(file)
    assert len(collection.items) == 3
    assert len(collection.flat_items) == 10
    assert len(collection) == 10
    assert collection[0]
    prevcategorical_code = -1
    for intent in collection.items.values():
        assert len(intent.samples) >= 3
        assert intent.categorical_code != prevcategorical_code
        prevcategorical_code = intent.categorical_code


@pytest.mark.parametrize(
    ["file", "method_name", "skip_condition"],
    [
        ("nonexistent.json", "parse_json", None),
        ("nonexistent.jsonl", "parse_jsonl", None),
        ("nonexistent.yaml", "parse_yaml", not pyyaml_available),
    ],
)
def test_dataset_exceptions(file, method_name, skip_condition):
    if skip_condition:
        pytest.skip(f"Skipping {file}: dependencies missing.")
    with pytest.raises(OSError) as e:
        _ = getattr(Dataset, method_name)(file)
        assert e


@pytest.mark.asyncio
async def test_mixin(testing_pipeline):
    REQUEST = "request"
    RESULT = "result"
    NAMESPACE = "namespace"

    class Model(AsyncMixin):
        def __init__(self, namespace_key: str = "default") -> None:
            super().__init__(namespace_key)

        async def predict(self, request: str):
            return RESULT

    ctx = Context()
    ctx.add_request(Message(text=REQUEST))
    model = Model(namespace_key=NAMESPACE)
    new_ctx: Context = await model(ctx, testing_pipeline)
    assert isinstance(new_ctx.framework_states[LABEL_KEY], dict)
    assert new_ctx.framework_states[LABEL_KEY][NAMESPACE] == RESULT
