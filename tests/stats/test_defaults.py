import pytest
from dff.script import Context
from dff.stats.defaults import get_current_label


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context,expected",
    [
        (Context(), set()),
        (Context(labels={0: ("a", "b")}), {("flow", "a"), ("node", "b"), ("label", "a: b")}),
    ],
)
async def test_get_current_label(context: Context, expected: set):
    result = await get_current_label(context, None, {"component": {"path": "."}})
    assert expected.intersection(set(result.items())) == expected
