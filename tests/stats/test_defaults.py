import pytest
from dff.script import Context
from dff.stats import defaults
from dff.stats import DFFInstrumentor


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context,expected",
    [
        (Context(), set()),
        (Context(labels={0: ("a", "b")}), {("flow", "a"), ("node", "b"), ("label", "a: b")}),
    ],
)
async def test_get_current_label(context: Context, expected: set):
    result = await defaults.get_current_label(context, None, {"component": {"path": "."}})
    assert expected.intersection(set(result.items())) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context,expected",
    [
        (Context(), set()),
        (Context(labels={0: ("a", "b")}), {("flow", "a"), ("node", "b"), ("label", "a: b")}),
    ],
)
async def test_otlp_integration(context, expected, tracer_exporter_and_provider, log_exporter_and_provider):
    _, tracer_provider = tracer_exporter_and_provider
    log_exporter, logger_provider = log_exporter_and_provider
    instrumentor = DFFInstrumentor()
    if instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.uninstrument()
    instrumentor.instrument(logger_provider=logger_provider, tracer_provider=tracer_provider)
    _ = await defaults.get_current_label(context, None, {"component": {"path": "."}})
    tracer_provider.force_flush()
    logger_provider.force_flush()
    assert len(log_exporter.get_finished_logs()) > 0
