# %%

import itertools
import re

from pydantic import ValidationError

from models_v2 import Flows, Flow, Node, Transition
from keywords import GLOBAL_TO_STATES, TO_STATES, RESPONSE, PROCESSING, GRAPH


def positive_test(samples, func):
    for sample in samples:
        try:
            func(sample)
        except ValidationError as exc:
            raise Exception(f"For {sample} got exeption {exc}")
        # func(sample)


def negative_test(samples, func):
    for sample in samples:
        try:
            res = func(sample)
            raise Exception(f"{sample} couldn't be passed but get {res.dict()}")
        except ValidationError:
            continue


def test_trasition():
    true_graph_name = ["flow_name", "123"]
    true_node_name = ["state_name", "123"]
    true_node_name_with_lambda = true_node_name + [lambda x: "state"]
    true_priorities = [123, 0, 0.1, -1, "123", "0", "0.1", "-1"]
    node_pointer_samples = (
        true_node_name_with_lambda
        + list(itertools.product(true_graph_name, true_node_name))
        + list(itertools.product(true_node_name, true_priorities))
        + list(itertools.product(true_graph_name, true_node_name, true_priorities))
    )
    condition_samples = ["sample", "123", re.compile("123"), any, [any, ["123", "123"]], 123]
    samples = list(itertools.product(node_pointer_samples, condition_samples))
    samples = [
        {
            GLOBAL_TO_STATES: {sample[0]: sample[1]},
            TO_STATES: {sample[0]: sample[1]},
        } for sample in samples
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
        {RESPONSE: [], PROCESSING: any},
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
                "node1": {RESPONSE: None, PROCESSING: any},
            },
        }
    ]

    negative_test(samples, Flow.parse_obj)
    print(f"{test_flow.__name__} passed")


def test_flows():
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
    positive_test(samples, Flows.parse_obj)
    # negative sampling
    samples = [{"flows": {}}]
    negative_test(samples, Flows.parse_obj)
    print(f"{test_flows.__name__} passed")


# test_to_state()
# test_cond()
# test_response()
# test_trasition()
# test_script()

test_trasition()
test_node()
test_flow()
test_flows()


# %%
