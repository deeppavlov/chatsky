import importlib
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.pipeline import Pipeline
from dff.script.core.keywords import RESPONSE, TRANSITIONS
import dff.script.conditions as cnd


dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


def test_pretty_format():
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.5_asynchronous_groups_and_services_full")
    example_module.pipeline.pretty_format()


@pytest.mark.parametrize("validation", (True, False))
def test_from_script_with_validation(validation):
    def response(ctx, pipeline: Pipeline):
        raise RuntimeError()

    script = {"": {"": {RESPONSE: response, TRANSITIONS: {"": cnd.true()}}}}

    if validation:
        with pytest.raises(ValueError):
            _ = Pipeline.from_script(script=script, start_label=("", ""), validation_stage=validation)
    else:
        _ = Pipeline.from_script(script=script, start_label=("", ""), validation_stage=validation)
