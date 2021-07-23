# %%

import re
import itertools

from pydantic import ValidationError
from data_model import ToState, Condition

# tests
def test_to_state():
    good_graphs = ["flow_name", "123"]
    good_states = ["state_name", "123"]
    good_states_with_lambda = good_states + [lambda x: "state"]
    good_priorities = [123, 0, 0.1, -1, "123", "0", "0.1", "-1"]
    samples = (
        good_states
        + list(itertools.product(good_graphs, good_states_with_lambda))
        + list(itertools.product(good_states_with_lambda, good_priorities))
        + list(itertools.product(good_graphs, good_states_with_lambda, good_priorities))
    )
    for sample in samples:
        try:
            ToState.parse(sample)
        except ValidationError as exc:
            print(sample)
            raise exc
    # negative sampling
    bad_states = [None]
    bad_priorities = ["0<zx", "0.1c", "<zx"]
    samples = list(itertools.product(good_graphs, bad_states, good_priorities)) + list(
        itertools.product(good_graphs, good_states, bad_priorities)
    )
    for sample in samples:
        try:
            res = ToState.parse(sample)
            raise Exception(f"{sample} couldn't be passed but get {res}")
        except ValidationError:
            continue


def test_cond():
    samples = ["sample", "123", re.compile("123"), any, [any, ["123", "123"]], 123]
    for sample in samples:
        try:
            Condition.parse(sample)
        except ValidationError as exc:
            print(sample)
            raise exc
    # negative sampling
    samples = [None]
    for sample in samples:
        try:
            res = Condition.parse(sample)
            raise Exception(f"{sample} couldn't be passed but get {res}")
        except ValidationError:
            continue


test_to_state()
test_cond()
