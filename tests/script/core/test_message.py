import pytest

from dff.script.core.message import Location, Attachment


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
            Attachment(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf", title="File"),
            Attachment(source="https://raw.githubusercontent.com/mathiasbynens/small/master/pdf.pdf", title="File"),
            True,
        ),
        (
            Attachment(source="https://github.com/mathiasbynens/small/raw/master/pdf.pdf", title="1"),
            Attachment(source="https://raw.githubusercontent.com/mathiasbynens/small/master/pdf.pdf", title="2"),
            False,
        ),
        (
            Attachment(source=__file__, title="File"),
            Attachment(source=__file__, title="File"),
            True,
        ),
        (
            Attachment(source=__file__, title="1"),
            Attachment(source=__file__, title="2"),
            False,
        ),
        (
            Attachment(id="1", title="File"),
            Attachment(id="2", title="File"),
            False,
        ),
    ],
)
def test_attachment(attachment1, attachment2, equal):
    assert (attachment1 == attachment2) == equal
