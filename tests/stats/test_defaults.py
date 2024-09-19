import importlib

import pytest

from chatsky.core import Context, Pipeline
from chatsky.core.service.types import ExtraHandlerRuntimeInfo, ServiceRuntimeInfo

try:
    from chatsky.stats import default_extractors
except ImportError:
    pytest.skip(allow_module_level=True, reason="One of the Opentelemetry packages is missing.")


async def test_get_current_label():
    context = Context()
    ctx.last_label = ("a", "b")
    pipeline = Pipeline(script={"greeting_flow": {"start_node": {}}}, start_label=("greeting_flow", "start_node"))
    runtime_info = ExtraHandlerRuntimeInfo(
        func=lambda x: x,
        stage="BEFORE",
        component=ServiceRuntimeInfo(
            path=".", name=".", timeout=None, asynchronous=False, execution_state={".": "FINISHED"}
        ),
    )
    result = await default_extractors.get_current_label(context, pipeline, runtime_info)
    assert result == {"flow": "a", "node": "b", "label": "a: b"}


async def test_otlp_integration(tracer_exporter_and_provider, log_exporter_and_provider):
    _, tracer_provider = tracer_exporter_and_provider
    log_exporter, logger_provider = log_exporter_and_provider
    tutorial_module = importlib.import_module("tutorials.stats.1_extractor_functions")
    tutorial_module.chatsky_instrumentor.uninstrument()
    tutorial_module.chatsky_instrumentor.instrument(logger_provider=logger_provider, tracer_provider=tracer_provider)
    runtime_info = ExtraHandlerRuntimeInfo(
        func=lambda x: x,
        stage="BEFORE",
        component=ServiceRuntimeInfo(
            path=".", name=".", timeout=None, asynchronous=False, execution_state={".": "FINISHED"}
        ),
    )
    ctx = Context()
    ctx.last_label = ("a", "b")
    _ = await default_extractors.get_current_label(ctx, tutorial_module.pipeline, runtime_info)
    tracer_provider.force_flush()
    logger_provider.force_flush()
    assert len(log_exporter.get_finished_logs()) > 0
