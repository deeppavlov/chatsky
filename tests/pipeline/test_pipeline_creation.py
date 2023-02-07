import pytest

from dff.pipeline import Pipeline
from dff.script.core.keywords import RESPONSE, TRANSITIONS
import dff.script.conditions as cnd


@pytest.mark.parametrize("validation", (True, False))
def test_from_script_with_validation(validation):
    def response(ctx, actor):
        raise RuntimeError()

    script = {"": {"": {RESPONSE: response, TRANSITIONS: {"": cnd.true()}}}}

    if validation:
        with pytest.raises(ValueError):
            _ = Pipeline.from_script(script=script, start_label=("", ""), validation_stage=validation)
    else:
        _ = Pipeline.from_script(script=script, start_label=("", ""), validation_stage=validation)
