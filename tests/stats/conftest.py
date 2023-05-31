import pytest
from dff.stats.instrumentor import resource
from dff.stats import InMemoryLogExporter
from dff.stats import InMemorySpanExporter
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk._logs import LoggerProvider


@pytest.fixture(scope="function")
def tracer_exporter_and_provider():
    exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    yield exporter, tracer_provider


@pytest.fixture(scope="function")
def log_exporter_and_provider():
    exporter = InMemoryLogExporter()
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    yield exporter, logger_provider


@pytest.fixture(scope="session")  # test saving configs to zip
def testing_cfg_dir(tmpdir_factory):
    cfg_dir = tmpdir_factory.mktemp("cfg")
    yield str(cfg_dir)


@pytest.fixture(scope="function")  # test saving to csv
def testing_file(tmpdir_factory):
    fn = tmpdir_factory.mktemp("data").join("stats.csv")
    return str(fn)
