# -*- coding: utf-8 -*-

from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.sdk._logs.export import InMemoryLogExporter, ConsoleLogExporter
from opentelemetry.sdk.metrics.export import InMemoryMetricReader, ConsoleMetricExporter
from .utils import get_wrapper_field, set_logger_destination, set_tracer_destination
from .instrumentor import OtelInstrumentor, OTLPMetricExporter, OTLPLogExporter, OTLPSpanExporter
