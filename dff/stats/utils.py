"""
Utils
-----
This module includes utilities designed for statistics collection.

"""
from opentelemetry._logs import get_logger_provider
from opentelemetry.trace import get_tracer_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

from dff.pipeline import ExtraHandlerRuntimeInfo


def configure_logger(endpoint: str = "grpc://localhost:4317"):
    get_logger_provider().add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True))
    )


def configure_tracer(endpoint: str = "grpc://localhost:4317"):
    get_tracer_provider().add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )


def get_wrapper_field(info: ExtraHandlerRuntimeInfo, postfix: str = "") -> str:
    """
    This function can be used to obtain a key, under which the wrapper data will be stored
    in the context.

    :param info: Handler runtime info obtained from the pipeline.
    :param postfix: Field-specific postfix that will be appended to the field name.
    """
    return f"{info['component']['path']}" + (f"-{postfix}" if postfix else "")
