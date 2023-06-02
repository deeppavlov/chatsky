import pytest

try:
    from dff.stats import defaults
    from dff.stats import DFFInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.trace import get_tracer_provider
    from opentelemetry.metrics import get_meter_provider
    from opentelemetry._logs import get_logger_provider
except ImportError:
    pytest.skip(allow_module_level=True, reason="One of the Opentelemetry packages is missing.")


def test_instrument_uninstrument():
    instrumentor = DFFInstrumentor()
    instrumentor.instrument()
    assert hasattr(defaults.get_current_label, "__wrapped__")
    assert hasattr(defaults.get_timing_before, "__wrapped__")
    assert hasattr(defaults.get_timing_after, "__wrapped__")
    instrumentor.uninstrument()
    assert not hasattr(defaults.get_current_label, "__wrapped__")
    assert not hasattr(defaults.get_timing_before, "__wrapped__")
    assert not hasattr(defaults.get_timing_after, "__wrapped__")


def test_keyword_arguments():
    instrumentor = DFFInstrumentor()
    assert instrumentor._meter_provider is get_meter_provider()
    assert instrumentor._logger_provider is get_logger_provider()
    assert instrumentor._tracer_provider is get_tracer_provider()
    instrumentor.instrument(
        tracer_provider=TracerProvider(), meter_provider=MeterProvider(), logger_provider=LoggerProvider()
    )
    assert instrumentor._meter_provider is not get_meter_provider()
    assert instrumentor._logger_provider is not get_logger_provider()
    assert instrumentor._tracer_provider is not get_tracer_provider()
