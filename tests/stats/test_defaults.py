import pytest

try:
    from wrapt import wrap_function_wrapper  # noqa: F401
    from dff.stats import OtelInstrumentor
except ImportError:
    pytest.skip(allow_module_level=True, reason="One of the Opentelemetry packages is missing.")

import importlib
from dff.script import Context
from dff.pipeline import Pipeline
from dff.pipeline.types import ExtraHandlerRuntimeInfo, ServiceRuntimeInfo
from dff.stats import default_extractors


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context,expected",
    [
        (Context(), {"flow": "greeting_flow", "label": "greeting_flow: start_node", "node": "start_node"}),
        (Context(labels={0: ("a", "b")}), {"flow": "a", "node": "b", "label": "a: b"}),
    ],
)
async def test_get_current_label(context: Context, expected: set):
    pipeline = Pipeline.from_script(
        {"greeting_flow": {"start_node": {}}},
        ("greeting_flow", "start_node"),
        validation_stage=False
    )
    runtime_info = ExtraHandlerRuntimeInfo(
        func=lambda x: x,
        stage="BEFORE",
        component=ServiceRuntimeInfo(
            path=".", name=".", timeout=None, asynchronous=False, execution_state={".": "FINISHED"}
        ),
    )
    result = await default_extractors.get_current_label(context, pipeline, runtime_info)
    assert result == expected


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
    example_module = importlib.import_module("tutorials.stats.1_extractor_functions")
    example_module.dff_instrumentor.uninstrument()
    example_module.dff_instrumentor.instrument(logger_provider=logger_provider, tracer_provider=tracer_provider)
    runtime_info = ExtraHandlerRuntimeInfo(
        func=lambda x: x,
        stage="BEFORE",
        component=ServiceRuntimeInfo(
            path=".", name=".", timeout=None, asynchronous=False, execution_state={".": "FINISHED"}
        ),
    )
    _ = await default_extractors.get_current_label(context, example_module.pipeline, runtime_info)
    tracer_provider.force_flush()
    logger_provider.force_flush()
    assert len(log_exporter.get_finished_logs()) > 0
