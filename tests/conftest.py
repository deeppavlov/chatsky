import sys

import pytest

from df_engine.core import Context

sys.path.insert(0, "../")

from examples.basic_example import actor

from df_slots.utils import register_storage, FORM_STORAGE_KEY, SLOT_STORAGE_KEY
from df_slots.root import root_slot


@pytest.fixture
def testing_actor():
    actor.handlers.clear()
    register_storage(actor, FORM_STORAGE_KEY)
    register_storage(actor, SLOT_STORAGE_KEY)
    yield actor


@pytest.fixture
def testing_context(testing_actor):
    ctx = testing_actor(Context())
    ctx.add_request("I am Groot")
    yield ctx


@pytest.fixture(scope="session")
def root():
    yield root_slot
