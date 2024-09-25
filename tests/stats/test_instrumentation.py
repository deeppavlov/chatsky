import pytest

from chatsky import Context
from chatsky.core.service import Service, ExtraHandlerRuntimeInfo, ComponentExecutionState, ServiceGroup
from tests.pipeline.utils import run_test_group

try:
    from chatsky.stats import default_extractors
    from chatsky.stats.instrumentor import logger as instrumentor_logger
    from chatsky.stats import OtelInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.trace import get_tracer_provider
    from opentelemetry.metrics import get_meter_provider
    from opentelemetry._logs import get_logger_provider
except ImportError:
    pytest.skip(allow_module_level=True, reason="One of the Opentelemetry packages is missing.")


def test_instrument_uninstrument():
    instrumentor = OtelInstrumentor()
    instrumentor.instrument()
    assert hasattr(default_extractors.get_current_label, "__wrapped__")
    assert hasattr(default_extractors.get_timing_before, "__wrapped__")
    assert hasattr(default_extractors.get_timing_after, "__wrapped__")
    instrumentor.uninstrument()
    assert not hasattr(default_extractors.get_current_label, "__wrapped__")
    assert not hasattr(default_extractors.get_timing_before, "__wrapped__")
    assert not hasattr(default_extractors.get_timing_after, "__wrapped__")


def test_keyword_arguments():
    instrumentor = OtelInstrumentor()
    assert instrumentor._meter_provider is get_meter_provider()
    assert instrumentor._logger_provider is get_logger_provider()
    assert instrumentor._tracer_provider is get_tracer_provider()
    instrumentor.instrument(
        tracer_provider=TracerProvider(), meter_provider=MeterProvider(), logger_provider=LoggerProvider()
    )
    assert instrumentor._meter_provider is not get_meter_provider()
    assert instrumentor._logger_provider is not get_logger_provider()
    assert instrumentor._tracer_provider is not get_tracer_provider()


def test_failed_stats_collection(log_event_catcher):
    chatsky_instrumentor = OtelInstrumentor.from_url("grpc://localhost:4317")
    chatsky_instrumentor.instrument()

    @chatsky_instrumentor
    async def bad_stats_collector(_: Context, __: ExtraHandlerRuntimeInfo):
        raise Exception

    service = Service(handler=lambda _: None, before_handler=bad_stats_collector)

    log_list = log_event_catcher(logger=instrumentor_logger, level="ERROR")

    assert run_test_group(ServiceGroup(components=[service])) == ComponentExecutionState.FINISHED

    assert len(log_list) == 1
