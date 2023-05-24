"""
Utils
-----
This module includes utilities designed for statistics collection.

"""
from typing import Optional
from . import exporter_patch
from opentelemetry._logs import get_logger_provider
from opentelemetry.trace import get_tracer_provider
from opentelemetry.metrics import get_meter_provider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter, SpanExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter, LogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter, MetricExporter

from dff.pipeline import ExtraHandlerRuntimeInfo


def set_logger_destination(exporter: Optional[LogExporter] = None):
    if exporter is None:
        exporter = OTLPLogExporter(endpoint="grpc://localhost:4317", insecure=True)
    get_logger_provider().add_log_record_processor(BatchLogRecordProcessor(exporter))


def set_meter_destination(exporter: Optional[MetricExporter] = None):
    if exporter is None:
        exporter = OTLPMetricExporter(endpoint="grpc://localhost:4317", insecure=True)
    get_meter_provider()._all_metric_readers.add(PeriodicExportingMetricReader(exporter))


def set_tracer_destination(exporter: Optional[SpanExporter] = None):
    if exporter is None:
        exporter = OTLPSpanExporter(endpoint="grpc://localhost:4317", insecure=True)
    get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))


def get_wrapper_field(info: ExtraHandlerRuntimeInfo, postfix: str = "") -> str:
    """
    This function can be used to obtain a key, under which the wrapper data will be stored
    in the context.

    :param info: Handler runtime info obtained from the pipeline.
    :param postfix: Field-specific postfix that will be appended to the field name.
    """
    path = info["component"]["path"].replace(".", "-")
    return f"{path}" + (f"-{postfix}" if postfix else "")
