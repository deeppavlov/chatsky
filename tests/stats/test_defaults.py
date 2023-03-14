import pytest
from dff.script import Context
from dff.stats.defaults import extract_current_label
from dff.stats import StatsRecord, ExtractorPool


def test_pool_constructor_type_checking():
    with pytest.raises(AssertionError) as e:
        ExtractorPool([1, 2])
    assert e


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context,expected",
    [
        (Context(), {("flow", ""), ("node", ""), ("label", "")}),
        (Context(labels={0: ("a", "b")}), {("flow", "a"), ("node", "b"), ("label", "a: b")}),
    ],
)
async def test_extract_current_label(context: Context, expected: set):
    result: StatsRecord = await extract_current_label(context, None, {"component": {"path": "."}})
    expected.intersection(set(result.data.items())) == expected
