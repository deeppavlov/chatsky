import importlib
import pytest

from dff.script import Message
from tests.test_utils import get_path_from_tests_to_current_dir
from dff.pipeline import Pipeline
from dff.script.core.keywords import RESPONSE, TRANSITIONS
import dff.script.conditions as cnd


dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


def test_pretty_format():
    tutorial_module = importlib.import_module(f"tutorials.{dot_path_to_addon}.5_asynchronous_groups_and_services_full")
    tutorial_module.pipeline.pretty_format()


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


def test_script_getting_and_setting():
    script = {"old_flow": {"": {RESPONSE: lambda c, p: Message(), TRANSITIONS: {"": cnd.true()}}}}
    pipeline = Pipeline.from_script(script=script, start_label=("old_flow", ""))

    new_script = {"new_flow": {"": {RESPONSE: lambda c, p: Message(), TRANSITIONS: {"": cnd.false()}}}}
    pipeline.set_actor(script=new_script, start_label=("new_flow", ""))
    assert list(pipeline.script.script.keys())[0] == list(new_script.keys())[0]
