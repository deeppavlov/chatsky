# %%

import re
import itertools

from pydantic import ValidationError

from models import ToState, Condition, Response, Transition, Node, Flow, Script
from keywords import GLOBAL_TO_STATES, TO_STATES, RESPONSE, PROCESSING, GRAPH


def positive_test(samples, func):
    for sample in samples:
        try:
            func(sample)
        except ValidationError as exc:
            raise Exception(f"For {sample} got exeption {exc.json()}")


def negative_test(samples, func):
    for sample in samples:
        try:
            res = func(sample)
            raise Exception(f"{sample} couldn't be passed but get {res.dict()}")
        except ValidationError:
            continue


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
    positive_test(samples, ToState.parse)
    # negative sampling
    bad_states = [None]
    bad_priorities = ["0<zx", "0.1c", "<zx"]
    samples = list(itertools.product(good_graphs, bad_states, good_priorities)) + list(
        itertools.product(good_graphs, good_states, bad_priorities)
    )
    negative_test(samples, ToState.parse)
    print(f"{test_to_state.__name__} passed")


def test_cond():
    samples = ["sample", "123", re.compile("123"), any, [any, ["123", "123"]], 123]
    positive_test(samples, Condition.parse)
    # negative sampling
    samples = [None, []]
    negative_test(samples, Condition.parse)
    print(f"{test_cond.__name__} passed")


def test_response():
    samples = ["sample", 123, ["123", 123], any]
    positive_test(samples, Response.parse)
    # negative sampling
    samples = [None, []]
    negative_test(samples, Response.parse)
    print(f"{test_response.__name__} passed")


def test_trasition():
    samples = [
        # {
        #     GLOBAL_TO_STATES: {any: re.compile("pattern")},
        # },
        {
            GLOBAL_TO_STATES: {any: "asd"},
            TO_STATES: {"213": any},
        },
    ]
    positive_test(samples, Transition.parse_obj)
    # negative sampling
    samples = [
        {
            GLOBAL_TO_STATES: {None: "asd"},
        },
        {
            TO_STATES: {"asd": []},
        },
        {
            GLOBAL_TO_STATES: {"asd": []},
        },
    ]
    negative_test(samples, Transition.parse_obj)
    print(f"{test_trasition.__name__} passed")


def test_node():
    samples = [
        {RESPONSE: ["123", 123], PROCESSING: any},
        {RESPONSE: "asd", PROCESSING: any},
        {RESPONSE: any, PROCESSING: any},
        {RESPONSE: any},
    ]
    positive_test(samples, Node.parse_obj)
    # negative sampling
    samples = [
        {RESPONSE: None, PROCESSING: any},
        {RESPONSE: "zxczxc", PROCESSING: "asd"},
        {RESPONSE: "zxczxc", PROCESSING: []},
        {RESPONSE: "zxczxc", PROCESSING: ["123"]},
    ]
    negative_test(samples, Node.parse_obj)
    print(f"{test_node.__name__} passed")


def test_flow():
    samples = [
        {
            GRAPH: {},
        },
        {
            GRAPH: {
                "node1": {RESPONSE: [123, "123"], PROCESSING: any},
                "node2": {RESPONSE: any, PROCESSING: any},
                "node3": {RESPONSE: any},
                "node4": {RESPONSE: "123", PROCESSING: any},
            },
        },
    ]
    positive_test(samples, Flow.parse_obj)
    # negative sampling
    samples = [
        {
            GRAPH: {
                "node1": {RESPONSE: [], PROCESSING: any},
            },
        }
    ]

    negative_test(samples, Flow.parse_obj)
    print(f"{test_flow.__name__} passed")


def test_script():
    samples = [
        {
            "flows": {
                "globals": {
                    GLOBAL_TO_STATES: {"213": any},
                    TO_STATES: {"213": any},
                    GRAPH: {
                        "node": {GLOBAL_TO_STATES: {"213": any}, RESPONSE: ["qweqwdqwd", ".git/"], PROCESSING: any}
                    },
                }
            }
        }
    ]
    positive_test(samples, Script.parse_obj)
    # negative sampling
    samples = [{}]
    negative_test(samples, Script.parse_obj)
    print(f"{test_script.__name__} passed")


test_to_state()
test_cond()
test_response()
test_trasition()
test_node()
test_flow()
test_script()

# %%
