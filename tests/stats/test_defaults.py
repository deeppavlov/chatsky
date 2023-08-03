import pytest

try:
    from wrapt import wrap_function_wrapper  # noqa: F401
    from dff.stats import OtelInstrumentor
except ImportError:
    pytest.skip(allow_module_level=True, reason="One of the Opentelemetry packages is missing.")

from dff.script import Context
from dff.pipeline.types import ExtraHandlerRuntimeInfo, ServiceRuntimeInfo
from dff.stats import default_extractors


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context,expected",
    [
        (Context(), set()),
        (Context(labels={0: ("a", "b")}), {("flow", "a"), ("node", "b"), ("label", "a: b")}),
    ],
)
async def test_get_current_label(context: Context, expected: set):
    result = await default_extractors.get_current_label(context, None, {"component": {"path": "."}})
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
    instrumentor = OtelInstrumentor()
    if instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.uninstrument()
    instrumentor.instrument(logger_provider=logger_provider, tracer_provider=tracer_provider)
    runtime_info = ExtraHandlerRuntimeInfo(
        func=lambda x: x,
        stage="BEFORE",
        component=ServiceRuntimeInfo(
            path=".", name=".", timeout=None, asynchronous=False, execution_state={".": "FINISHED"}
        ),
    )
    _ = await default_extractors.get_current_label(context, None, runtime_info)
    tracer_provider.force_flush()
    logger_provider.force_flush()
    assert len(log_exporter.get_finished_logs()) > 0
