import pytest
from pydantic import ValidationError

from chatsky.script import Message
from chatsky.slots.slots import (
    RegexpSlot,
    GroupSlot,
    FunctionSlot,
    SlotNotExtracted,
    ExtractedValueSlot,
    ExtractedGroupSlot,
)


@pytest.mark.parametrize(
    ("user_request", "regexp", "expected"),
    [
        (
            Message(text="My name is Bot"),
            "(?<=name is ).+",
            ExtractedValueSlot.model_construct(extracted_value="Bot", is_slot_extracted=True, default_value=None),
        ),
        (
            Message(text="I won't tell you my name"),
            "(?<=name is ).+$",
            ExtractedValueSlot.model_construct(
                extracted_value=SlotNotExtracted(
                    "Failed to match pattern {regexp!r} in {request_text!r}.".format(
                        regexp="(?<=name is ).+$", request_text="I won't tell you my name"
                    )
                ),
                is_slot_extracted=False,
                default_value=None,
            ),
        ),
    ],
)
async def test_regexp(user_request, regexp, expected, context, pipeline):
    context.add_request(user_request)
    slot = RegexpSlot(regexp=regexp)
    result = await slot.get_value(context, pipeline)
    assert result == expected


@pytest.mark.parametrize(
    ("user_request", "func", "expected"),
    [
        (
            Message(text="I am bot"),
            lambda msg: msg.text.split(" ")[2],
            ExtractedValueSlot.model_construct(extracted_value="bot", is_slot_extracted=True, default_value=None),
        ),
        (
            Message(text="My email is bot@bot"),
            lambda msg: [i for i in msg.text.split(" ") if "@" in i][0],
            ExtractedValueSlot.model_construct(extracted_value="bot@bot", is_slot_extracted=True, default_value=None),
        ),
    ],
)
async def test_function(user_request, func, expected, context, pipeline):
    context.add_request(user_request)
    slot = FunctionSlot(func=func)
    result = await slot.get_value(context, pipeline)
    assert result == expected

    async def async_func(*args, **kwargs):
        return func(*args, **kwargs)

    slot = FunctionSlot(func=async_func)
    result = await slot.get_value(context, pipeline)
    assert result == expected


async def test_function_exception(context, pipeline):
    def func(msg: Message):
        raise RuntimeError("error")

    slot = FunctionSlot(func=func)
    result = await slot.get_value(context, pipeline)
    assert result.is_slot_extracted is False
    assert isinstance(result.extracted_value, RuntimeError)


@pytest.mark.parametrize(
    ("user_request", "slot", "expected", "is_extracted"),
    [
        (
            Message(text="I am Bot. My email is bot@bot"),
            GroupSlot(
                name=RegexpSlot(regexp=r"(?<=am ).+?(?=\.)"),
                email=RegexpSlot(regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+"),
            ),
            ExtractedGroupSlot(
                name=ExtractedValueSlot.model_construct(
                    is_slot_extracted=True, extracted_value="Bot", default_value=None
                ),
                email=ExtractedValueSlot.model_construct(
                    is_slot_extracted=True, extracted_value="bot@bot", default_value=None
                ),
            ),
            True,
        ),
        (
            Message(text="I am Bot. I won't tell you my email"),
            GroupSlot(
                name=RegexpSlot(regexp=r"(?<=am ).+?(?=\.)"),
                email=RegexpSlot(regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+"),
            ),
            ExtractedGroupSlot(
                name=ExtractedValueSlot.model_construct(
                    is_slot_extracted=True, extracted_value="Bot", default_value=None
                ),
                email=ExtractedValueSlot.model_construct(
                    is_slot_extracted=False,
                    extracted_value=SlotNotExtracted(
                        "Failed to match pattern {regexp!r} in {request_text!r}.".format(
                            regexp=r"[a-zA-Z\.]+@[a-zA-Z\.]+", request_text="I am Bot. I won't tell you my email"
                        )
                    ),
                    default_value=None,
                ),
            ),
            False,
        ),
    ],
)
async def test_group_slot_extraction(user_request, slot, expected, is_extracted, context, pipeline):
    context.add_request(user_request)
    result = await slot.get_value(context, pipeline)
    assert result == expected
    assert result.__slot_extracted__ == is_extracted


@pytest.mark.parametrize("forbidden_name", ["__dunder__", "contains.dot"])
def test_group_subslot_name_validation(forbidden_name):
    with pytest.raises(ValidationError):
        GroupSlot(**{forbidden_name: RegexpSlot(regexp="")})


async def test_str_representation():
    assert (
        str(ExtractedValueSlot.model_construct(is_slot_extracted=True, extracted_value="hello", default_value=None))
        == "hello"
    )
    assert (
        str(ExtractedValueSlot.model_construct(is_slot_extracted=False, extracted_value=None, default_value="hello"))
        == "hello"
    )
    assert (
        str(
            ExtractedGroupSlot(
                first_name=ExtractedValueSlot.model_construct(
                    is_slot_extracted=True, extracted_value="Tom", default_value="John"
                ),
                last_name=ExtractedValueSlot.model_construct(
                    is_slot_extracted=False, extracted_value=None, default_value="Smith"
                ),
            )
        )
        == "{'first_name': 'Tom', 'last_name': 'Smith'}"
    )
