import importlib

from dff.script import Message
from tests.test_utils import get_path_from_tests_to_current_dir
from dff.pipeline import Pipeline
from dff.script.core.keywords import RESPONSE, TRANSITIONS
import dff.script.conditions as cnd


dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


def test_pretty_format():
    tutorial_module = importlib.import_module(f"tutorials.{dot_path_to_addon}.5_asynchronous_groups_and_services_full")
    tutorial_module.pipeline.pretty_format()


def test_script_getting_and_setting():
    script = {"old_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: {"": cnd.true()}}}}
    pipeline = Pipeline.from_script(script=script, start_label=("old_flow", ""))

    new_script = {"new_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: {"": cnd.false()}}}}
    pipeline.set_actor(script=new_script, start_label=("new_flow", ""))
    assert list(pipeline.script.script.keys())[0] == list(new_script.keys())[0]
