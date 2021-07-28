# %%
from typing import Callable
import itertools
import re
import random

from pydantic import ValidationError

from flows import Flows, Flow, Node, Transition
from context import Context
from keywords import GLOBAL_TO_STATES, TO_STATES, RESPONSE, PROCESSING, GRAPH

# TODO: full, correct test for normalize_* , validate_flows


def positive_test(samples, func):
    results = []
    for sample in samples:
        try:
            res = func(sample)
            results += [res]
        except ValidationError as exeption:
            raise Exception(f"For {sample} got {exeption=}")
    return results


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
    true_node_name_with_lambda = true_node_name + [lambda c, f: "state"]
    true_priorities = [123, 0, 0.1, -1, "123", "0", "0.1", "-1"]
    node_label_samples = (
        true_node_name_with_lambda
        + list(itertools.product(true_graph_name, true_node_name))
        + list(itertools.product(true_node_name, true_priorities))
        + list(itertools.product(true_graph_name, true_node_name, true_priorities))
    )
    condition_samples = [
        "sample",
        "123",
        re.compile("123"),
        lambda c, f: True,
        [any, ["123", all, [lambda c, f: True, "123"]]],
        [all, ["123", re.compile("123"), "sample"]],
        123,
    ]
    samples = list(itertools.product(node_label_samples, condition_samples))
    samples = [
        {
            GLOBAL_TO_STATES: {sample[0]: sample[1]},
            TO_STATES: {sample[0]: sample[1]},
        }
        for sample in samples
    ]
    results = positive_test(samples, Transition.parse_obj)
    results = [res.get_transitions("root", 1.0) for res in results] + [
        res.get_transitions("root", 1.0, True) for res in results
    ]
    flows = Flows.parse_obj({"flows": {"globals": {}}})
    context = Context()
    context.add_human_utterance("text")
    for res in results:
        for node_label, cond in res.items():
            if not (
                isinstance(node_label, Callable)
                or (isinstance(node_label[0], str) and isinstance(node_label[1], str), isinstance(node_label[2], float))
            ):
                raise ValueError(f"unecpected {node_label=}")
            if not (isinstance(cond, Callable) and isinstance(cond(context, flows), bool)):
                raise ValueError(f"unecpected {cond=}")

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
        {RESPONSE: lambda c, f: "response", PROCESSING: any},
        {RESPONSE: lambda c, f: "response"},
    ]
    results = positive_test(samples, Node.parse_obj)
    flows = Flows.parse_obj({"flows": {"globals": {}}})
    context = Context()
    for res in results:
        response = res.get_response()
        if not isinstance(response, Callable):
            raise ValueError(f"unecpected {response=} for node {res}")
        random.seed(31415)
        response_res = response(context, flows)
        if not isinstance(response_res, str):
            raise ValueError(f"unecpected {response_res=} for node {res}")
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


test_trasition()
test_node()
test_flow()
test_flows()


# %%
