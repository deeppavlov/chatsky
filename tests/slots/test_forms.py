import pytest
import math

from dff.pipeline import Pipeline
from dff.script.slots import root_slot, RegexpSlot, FormPolicy, FormState, FORM_STORAGE_KEY


@pytest.fixture
def testing_form(testing_pipeline: Pipeline):
    root_slot.children.clear()
    regexp_slot = RegexpSlot(name="tr", regexp=".+")
    form_policy = FormPolicy(name="testing_form", mapping={regexp_slot.name: [testing_pipeline.actor.start_label[:2]]})
    yield form_policy


def test_state_update(testing_context, testing_pipeline, testing_form: FormPolicy):
    testing_form.update_state(FormState.ACTIVE)(testing_context, testing_pipeline)
    assert testing_context.framework_states[FORM_STORAGE_KEY][testing_form.name] == FormState.ACTIVE
    assert testing_form.has_state(FormState.ACTIVE)(testing_context, testing_pipeline) is True


def test_next_slot(testing_context, testing_pipeline, testing_form: FormPolicy):
    next_label = testing_form.to_next_label()(testing_context, testing_pipeline)
    assert next_label == (*testing_pipeline.actor.start_label[:2], 1.0)
    testing_form.mapping.clear()
    next_label = testing_form.to_next_label()(testing_context, testing_pipeline)
    assert next_label == (*testing_pipeline.actor.fallback_label[:2], -math.inf)
