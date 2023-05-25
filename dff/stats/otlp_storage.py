from typing import Optional

from .record import StatsRecord
from .subscriber import PoolSubscriber
from . import exporter_patch  # noqa: F401

from opentelemetry.sdk.resources import Resource
from opentelemetry._logs import set_logger_provider, get_logger_provider, get_logger, SeverityNumber
from opentelemetry.trace import get_tracer, SpanKind, get_tracer_provider, set_tracer_provider, Span
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter, SpanExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter, LogExporter

resource = Resource.create({"service.name": "dialog_flow_framework"})
tracer_provider = TracerProvider(resource=resource)
logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)
set_tracer_provider(tracer_provider)


class OpenTelemetryStorage(PoolSubscriber):
    """
    Opentelemetry provides its own abstractions to batch and export trace data.
    and deal with thread safety.
    For this reason, this class does not implement item batching and locks,
    unlike the regular storage.
    """

    def __init__(self) -> None:
        self._tracer = get_tracer(__name__)
        self._logger = get_logger(__name__)

    async def on_record_event(self, record: StatsRecord):
        span: Span
        with self._tracer.start_as_current_span(f"dff{record.data_key}", kind=SpanKind.INTERNAL) as span:
            span_ctx = span.get_span_context()
            record = LogRecord(
                observed_timestamp=record.timestamp.timestamp(),
                span_id=span_ctx.span_id,
                trace_id=span_ctx.trace_id,
                body=record.data,
                trace_flags=span_ctx.trace_flags,
                severity_text=None,
                severity_number=SeverityNumber(1),
                resource=resource,
                attributes={"context_id": record.context_id, "request_id": record.request_id},
            )
            self._logger.emit(record=record)

    @staticmethod
    def set_logger_destination(exporter: Optional[LogExporter] = None):
        """
        Configure global logger destination (e.g. console, memory, or OTLP collector).
        """
        if exporter is None:
            exporter = OTLPLogExporter(endpoint="grpc://localhost:4317", insecure=True)
        get_logger_provider().add_log_record_processor(BatchLogRecordProcessor(exporter))

    @staticmethod
    def set_tracer_destination(exporter: Optional[SpanExporter] = None):
        """
        Configure global logger destination (e.g. console, memory, or OTLP collector).
        """
        if exporter is None:
            exporter = OTLPSpanExporter(endpoint="grpc://localhost:4317", insecure=True)
        get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))
