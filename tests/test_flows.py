# %%
from typing import Callable
import itertools
import re
import random

from dff.core import Flows, Flow, Node, Actor, Context
from dff.core.keywords import GLOBAL_TRANSITIONS, TRANSITIONS, RESPONSE, PROCESSING, GRAPH


# TODO: full, correct test for normalize_* , validate_flows


def positive_test(samples, custom_class):
    results = []
    for sample in samples:
        try:
            res = custom_class(**sample)
            results += [res]
        except Exception as exeption:
            raise Exception(f"For {sample} got {exeption=}")
    return results


def negative_test(samples, custom_class):
    for sample in samples:
        try:
            res = custom_class(**sample)
            raise Exception(f"{sample} couldn't be passed but get {res.dict()}")
        except Exception:
            continue


def trasition_test(model, transition_name, additional_data):
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
    samples = [{transition_name: {sample[0]: sample[1]}, **additional_data} for sample in samples]
    results = positive_test(samples, model)
    results = [res.get_transitions("root", 1.0) for res in results] + [
        res.get_transitions("root", 1.0, True) for res in results
    ]
    actor = Actor({"globals": {GRAPH: {"globals": {RESPONSE: "123"}}}}, ("globals", "globals"))
    ctx = Context()
    ctx.add_request("text")
    for res in results:
        for node_label, cond in res.items():
            if not (
                isinstance(node_label, Callable)
                or (isinstance(node_label[0], str) and isinstance(node_label[1], str), isinstance(node_label[2], float))
            ):
                raise ValueError(f"unexpected {node_label=}")
            if not (isinstance(cond, Callable) and isinstance(cond(ctx, actor), bool)):
                raise ValueError(f"unexpected {cond=}")

    # negative sampling
    samples = [
        {transition_name: {None: "asd"}, **additional_data},
        {transition_name: {"asd": []}, **additional_data},
    ]
    negative_test(samples, model)
    # print(f"{trasition_test.__name__} passed")


def test_node():
    trasition_test(Node, TRANSITIONS, {RESPONSE: ["123", 123], PROCESSING: any})
    samples = [
        {RESPONSE: ["123", 123], PROCESSING: any},
        {RESPONSE: "asd", PROCESSING: any},
        {RESPONSE: lambda c, f: "response", PROCESSING: any},
        {RESPONSE: lambda c, f: "response"},
    ]
    results = positive_test(samples, Node)
    actor = Actor({"globals": {GRAPH: {"globals": {RESPONSE: "123"}}}}, ("globals", "globals"))
    ctx = Context()
    for res in results:
        response = res.get_response()
        if not isinstance(response, Callable):
            raise ValueError(f"unexpected {response=} for node {res}")
        random.seed(31415)
        response_res = response(ctx, actor)
        if not isinstance(response_res, str):
            raise ValueError(f"unexpected {response_res=} for node {res}")
    # negative sampling
    samples = [
        {RESPONSE: [], PROCESSING: any},
        {RESPONSE: None, PROCESSING: any},
        {RESPONSE: "zxczxc", PROCESSING: any, "asdasdas": any},
        {RESPONSE: "zxczxc", PROCESSING: "asd"},
        {RESPONSE: "zxczxc", PROCESSING: []},
        {RESPONSE: "zxczxc", PROCESSING: ["123"]},
    ]
    negative_test(samples, Node)
    # print(f"{test_node.__name__} passed")


def test_flow():
    trasition_test(Flow, GLOBAL_TRANSITIONS, {GRAPH: {}})
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
    positive_test(samples, Flow)
    # negative sampling
    samples = [
        {
            GRAPH: {
                "node1": {RESPONSE: None, PROCESSING: any},
            },
        },
        {
            GRAPH: {
                "node1": {RESPONSE: "", PROCESSING: any, "asdasdas": any},
            },
        },
    ]

    negative_test(samples, Flow)
    # print(f"{test_flow.__name__} passed")


def test_flows():
    samples = [
        {
            "flows": {
                "globals": {
                    GLOBAL_TRANSITIONS: {"213": any},
                    GRAPH: {"node": {TRANSITIONS: {"213": any}, RESPONSE: ["qweqwdqwd", ".git/"], PROCESSING: any}},
                }
            }
        }
    ]
    positive_test(samples, Flows)
    # negative sampling
    samples = [{"flows": {}}]
    negative_test(samples, Flows)
    # print(f"{test_flows.__name__} passed")
