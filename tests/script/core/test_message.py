import pytest
from pydantic import ValidationError, HttpUrl, FilePath

from dff.script.core.message import Location, DataAttachment, Keyboard, Button


def test_location():
    loc1 = Location(longitude=-0.1, latitude=-0.1)
    loc2 = Location(longitude=-0.09999, latitude=-0.09998)
    loc3 = Location(longitude=-0.10002, latitude=-0.10001)

    assert loc1 == loc2
    assert loc3 == loc1
    assert loc2 != loc3

    assert loc1 != 1


@pytest.mark.parametrize(
    "attachment1,attachment2,equal",
    [
        (
            DataAttachment(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf", title="File"),
            DataAttachment(source="https://raw.githubusercontent.com/mathiasbynens/small/master/pdf.pdf", title="File"),
            True,
        ),
        (
            DataAttachment(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf", title="1"),
            DataAttachment(source="https://raw.githubusercontent.com/mathiasbynens/small/master/pdf.pdf", title="2"),
            False,
        ),
        (
            DataAttachment(source=__file__, title="File"),
            DataAttachment(source=__file__, title="File"),
            True,
        ),
        (
            DataAttachment(source=__file__, title="1"),
            DataAttachment(source=__file__, title="2"),
            False,
        ),
        (
            DataAttachment(id="1", title="File"),
            DataAttachment(id="2", title="File"),
            False,
        ),
    ],
)
def test_attachment(attachment1, attachment2, equal):
    assert (attachment1 == attachment2) == equal


def test_missing_error():
    with pytest.raises(ValidationError) as e:
        _ = DataAttachment(source=HttpUrl("http://google.com"), id="123")
    assert e

    with pytest.raises(ValidationError) as e:
        _ = DataAttachment(source=FilePath("/etc/missing_file"))
    assert e


def test_empty_keyboard():
    with pytest.raises(ValidationError) as e:
        _ = Keyboard(buttons=[])
    assert e


def test_long_button_data():
    with pytest.raises(ValidationError) as error:
        Button(text="", data="test" * 64)
    assert error
