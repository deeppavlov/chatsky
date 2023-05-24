import pytest
from dff.script import Context
from dff.stats.defaults import extract_current_label, default_extractor_pool
from dff.stats import StatsRecord


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context,expected",
    [
        (Context(), set()),
        (Context(labels={0: ("a", "b")}), {("flow", "a"), ("node", "b"), ("label", "a: b")}),
    ],
)
async def test_extract_current_label(context: Context, expected: set):
    result: StatsRecord = await extract_current_label(context, None, {"component": {"path": "."}})
    assert expected.intersection(set(result.data.items())) == expected


def test_misc():
    all_handlers = default_extractor_pool.all_handlers
    assert isinstance(all_handlers, list)
    assert len(all_handlers) == 3
    before = default_extractor_pool.before
    assert isinstance(before, list)
    assert len(before) == 1
