import os
import importlib

import pytest

from tests.test_utils import get_path_from_tests_to_current_dir

from dff.utils.testing.common import check_happy_path

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    ["example_module_name", "skip_condition"],
    [
        ("1_base_example", None),
        ("7_rasa", os.getenv("RASA_API_KEY") is None),
        (
            "5_dialogflow",
            not (os.getenv("GDF_ACCOUNT_JSON") and os.path.exists(os.getenv("GDF_ACCOUNT_JSON")))),
        # ("6_hf_api", os.getenv("HF_API_KEY") is None),
        ("2_gensim_example", None),
        ("4_sklearn_example", None),
    ],
)
def test_examples(example_module_name: str, skip_condition):
    if skip_condition:
        pytest.skip()
    module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    pipeline = getattr(module, "pipeline")
    happy_path = getattr(module, "happy_path")
    check_happy_path(pipeline, happy_path)
