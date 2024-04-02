from typing import Dict
from dff.pipeline import Pipeline
from dff.script import PRE_RESPONSE_PROCESSING, PRE_TRANSITIONS_PROCESSING, RESPONSE, TRANSITIONS, Context, Message, Script, NodeLabel3Type
from dff.script.conditions import exact_match
from dff.script.labels import repeat


def wrong_param_number(number: int) -> float:
    return 8.0 + number


def wrong_param_types(number: int, flag: bool) -> float:
    return 8.0 + number if flag else 42.1


def wrong_return_type(_: Context, __: Pipeline) -> float:
    return 1.0


def correct_label(_: Context, __: Pipeline) -> NodeLabel3Type:
    return ("root", "start", 1)


def correct_response(_: Context, __: Pipeline) -> Message:
    return Message("hi")


def correct_condition(_: Context, __: Pipeline) -> bool:
    return True


def correct_pre_response_processor(_: Context, __: Pipeline) -> None:
    pass


def correct_pre_transition_processor(_: Context, __: Pipeline) -> None:
    pass


def function_signature_test(message: str, param_number: Dict, param_types: Dict, return_type: Dict):
    for script, error in zip([param_number, param_types, return_type], ["param number", "param types", "return type"]):
        try:
            Script(script=script)
            raise Exception(f"can not be passed: {message}: {error}")
        except ValueError:
            pass


def test_labels():
    param_number_script = {"root": { "start": { TRANSITIONS: { wrong_param_number: exact_match(Message("hi")) } } } }
    param_types_script = {"root": { "start": { TRANSITIONS: { wrong_param_types: exact_match(Message("hi")) } } } }
    return_type_script = {"root": { "start": { TRANSITIONS: { wrong_return_type: exact_match(Message("hi")) } } } }
    function_signature_test("wrong label function signature", param_number_script, param_types_script, return_type_script)
    try:
        # wrong label tuple flow
        Script(script={"root": { "start": { TRANSITIONS: { ("other", "start", 1): exact_match(Message("hi")) } } } })
        raise Exception("can not be passed: wrong label tuple flow")
    except ValueError:
        pass
    try:
        # wrong label tuple node
        Script(script={"root": { "start": { TRANSITIONS: { ("root", "other", 1): exact_match(Message("hi")) } } } })
        raise Exception("can not be passed: wrong label tuple node")
    except ValueError:
        pass
    Script(script={"root": { "start": { TRANSITIONS: { correct_label: exact_match(Message("hi")) } } } })


def test_responses():
    param_number_script = {"root": { "start": { RESPONSE: { repeat: wrong_param_number } } } }
    param_types_script = {"root": { "start": { RESPONSE: { repeat: wrong_param_types } } } }
    return_type_script = {"root": { "start": { RESPONSE: { repeat: wrong_return_type } } } }
    function_signature_test("wrong response function signature", param_number_script, param_types_script, return_type_script)
    try:
        # wrong response type
        Script(script={"root": { "start": { RESPONSE: { repeat: 7 } } } })
        raise Exception("can not be passed: wrong response type")
    except ValueError:
        pass
    Script(script={"root": { "start": { RESPONSE: { repeat: correct_response } } } })


def test_conditions():
    param_number_script = {"root": { "start": { TRANSITIONS: { ("root", "start", 1): wrong_param_number } } } }
    param_types_script = {"root": { "start": { TRANSITIONS: { ("root", "start", 1): wrong_param_types } } } }
    return_type_script = {"root": { "start": { TRANSITIONS: { ("root", "start", 1): wrong_return_type } } } }
    function_signature_test("wrong condition function signature", param_number_script, param_types_script, return_type_script)
    try:
        # wrong condition type
        Script(script={"root": { "start": { TRANSITIONS: { ("root", "start", 1): 7 } } } })
        raise Exception("can not be passed: wrong condition type")
    except ValueError:
        pass
    Script(script={"root": { "start": { TRANSITIONS: { ("root", "start", 1): correct_condition } } } })


def test_processing():
    param_number_script = {"root": { "start": { PRE_RESPONSE_PROCESSING: { "PRP": wrong_param_number } } } }
    param_types_script = {"root": { "start": { PRE_RESPONSE_PROCESSING: { "PRP": wrong_param_types } } } }
    return_type_script = {"root": { "start": { PRE_RESPONSE_PROCESSING: { "PRP": wrong_return_type } } } }
    function_signature_test("wrong pre-response processing function signature", param_number_script, param_types_script, return_type_script)
    param_number_script = {"root": { "start": { PRE_TRANSITIONS_PROCESSING: { "PTP": wrong_param_number } } } }
    param_types_script = {"root": { "start": { PRE_TRANSITIONS_PROCESSING: { "PTP": wrong_param_types } } } }
    return_type_script = {"root": { "start": { PRE_TRANSITIONS_PROCESSING: { "PTP": wrong_return_type } } } }
    function_signature_test("wrong pre-transitions processing function signature", param_number_script, param_types_script, return_type_script)
    try:
        # wrong pre-response processing type
        Script(script={"root": { "start": { PRE_RESPONSE_PROCESSING: { "PRP": 42 } } } })
        raise Exception("can not be passed: wrong pre-response processing type")
    except ValueError:
        pass
    try:
        # wrong pre-transitions processing type
        Script(script={"root": { "start": { PRE_TRANSITIONS_PROCESSING: { "PTP": 42 } } } })
        raise Exception("can not be passed: wrong pre-transitions processing type")
    except ValueError:
        pass
    Script(script={"root": { "start": { PRE_RESPONSE_PROCESSING: { "PRP": correct_pre_response_processor } } } })
    Script(script={"root": { "start": { PRE_TRANSITIONS_PROCESSING: { "PTP": correct_pre_transition_processor } } } })
