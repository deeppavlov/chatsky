import importlib

import pytest

from chatsky.core import Context
from chatsky.core.service import Service
from chatsky.core.service.types import ExtraHandlerRuntimeInfo

try:
    from chatsky.stats import default_extractors
except ImportError:
    pytest.skip(allow_module_level=True, reason="One of the Opentelemetry packages is missing.")


async def test_get_current_label():
    context = Context.init(("a", "b"))
    runtime_info = ExtraHandlerRuntimeInfo(
        func=lambda x: x,
        stage="BEFORE",
        component=Service(handler=lambda ctx: None, path="-", name="-", timeout=None, concurrent=False),
    )
    result = await default_extractors.get_current_label(context, runtime_info)
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
        component=Service(handler=lambda ctx: None, path="-", name="-", timeout=None, concurrent=False),
    )
    _ = await default_extractors.get_current_label(Context.init(("a", "b")), runtime_info)
    tracer_provider.force_flush()
    logger_provider.force_flush()
    assert len(log_exporter.get_finished_logs()) > 0
