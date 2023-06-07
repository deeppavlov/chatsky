import pytest

try:
    from dff.stats import InMemoryLogExporter, InMemorySpanExporter, OTLPLogExporter, OTLPSpanExporter
    from dff.stats.instrumentor import resource
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk._logs import LoggerProvider

    opentelemetry_available = True
except ImportError:
    opentelemetry_available = False


@pytest.fixture(scope="function")
def tracer_exporter_and_provider():
    if not opentelemetry_available:
        pytest.skip("One of the Opentelemetry packages is missing.")
    exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter, schedule_delay_millis=900))
    yield exporter, tracer_provider


@pytest.fixture(scope="function")
def log_exporter_and_provider():
    if not opentelemetry_available:
        pytest.skip("One of the Opentelemetry packages is missing.")
    exporter = InMemoryLogExporter()
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter, schedule_delay_millis=900))
    yield exporter, logger_provider


@pytest.fixture(scope="function")
def otlp_trace_exp_provider():
    if not opentelemetry_available:
        pytest.skip("One of the Opentelemetry packages is missing.")
    exporter = OTLPSpanExporter("grpc://localhost:4317", insecure=True)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter, schedule_delay_millis=900))
    yield exporter, tracer_provider


@pytest.fixture(scope="function")
def otlp_log_exp_provider():
    if not opentelemetry_available:
        pytest.skip("One of the Opentelemetry packages is missing.")
    exporter = OTLPLogExporter("grpc://localhost:4317", insecure=True)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter, schedule_delay_millis=900))
    yield exporter, logger_provider


@pytest.fixture(scope="session")  # test saving configs to zip
def testing_cfg_dir(tmpdir_factory):
    cfg_dir = tmpdir_factory.mktemp("cfg")
    yield str(cfg_dir)


@pytest.fixture(scope="function")  # test saving to csv
def testing_file(tmpdir_factory):
    fn = tmpdir_factory.mktemp("data").join("stats.csv")
    return str(fn)
