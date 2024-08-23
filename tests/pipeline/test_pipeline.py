from chatsky.script import Message
from chatsky.pipeline import Pipeline
from chatsky.script.core.keywords import RESPONSE, TRANSITIONS
import chatsky.script.conditions as cnd


def test_script_getting_and_setting():
    script = {"old_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: {"": cnd.true()}}}}
    pipeline = Pipeline(script=script, start_label=("old_flow", ""))

    new_script = {"new_flow": {"": {RESPONSE: lambda _, __: Message(), TRANSITIONS: {"": cnd.false()}}}}
    # IDE gives the warning that "Property 'script' cannot be set"
    # And yet the test still passes.
    pipeline.script = new_script
    pipeline.start_label = ("new_flow", "")
    assert list(pipeline.script.keys())[0] == list(new_script.keys())[0]
