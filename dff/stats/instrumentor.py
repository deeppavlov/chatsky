"""
Instrumentor
-------------
This modules contains the :py:class:`~OtelInstrumentor` class that implements
Opentelemetry's `BaseInstrumentor` interface and allows for automated
instrumentation of Dialog Flow Framework applications,
e.g. for automated logging and log export.

For detailed reference, see `~OtelInstrumentor` class.
"""
import asyncio
from typing import Collection, Optional

from wrapt import wrap_function_wrapper, decorator
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.metrics import get_meter, get_meter_provider, Meter
from opentelemetry.trace import get_tracer, get_tracer_provider, Tracer
from opentelemetry._logs import get_logger, get_logger_provider, Logger, SeverityNumber
from opentelemetry.trace import SpanKind, Span
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

from dff.script.core.context import get_last_index
from dff.stats.utils import (
    resource,
    get_wrapper_field,
    set_logger_destination,
    set_meter_destination,
    set_tracer_destination,
)
from dff.stats import default_extractors


INSTRUMENTS = ["dff"]


class OtelInstrumentor(BaseInstrumentor):
    """
    Utility class for instrumenting DFF-related functions
    that implements the :py:class:`~BaseInstrumentor` interface.
    :py:meth:`~instrument` and :py:meth:`~uninstrument` methods
    are available to apply and revert the instrumentation effects,
    e.g. enable and disable logging at runtime.

    .. code-block::

        dff_instrumentor = OtelInstrumentor()
        dff_instrumentor.instrument()
        dff_instrumentor.uninstrument()

    Opentelemetry provider instances can be optionally passed to the class constructor.
    Otherwise, the global logger, tracer and meter providers are leveraged.

    The class implements the :py:meth:`~__call__` method, so that
    regular functions can be decorated using the class instance.

    .. code-block::

        @dff_instrumentor
        async def function(context, pipeline, runtime_info):
            ...

    :param logger_provider: Opentelemetry logger provider. Used to construct a logger instance.
    :param tracer_provider: Opentelemetry tracer provider. Used to construct a tracer instance.
    :parame meter_provider: Opentelemetry meter provider. Used to construct a meter instance.
    """

    def __init__(self, logger_provider=None, tracer_provider=None, meter_provider=None) -> None:
        super().__init__()
        self._logger_provider: Optional[LoggerProvider] = None
        self._tracer_provider: Optional[TracerProvider] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._logger: Optional[Logger] = None
        self._tracer: Optional[Tracer] = None
        self._meter: Optional[Meter] = None
        self._configure_providers(
            logger_provider=logger_provider, tracer_provider=tracer_provider, meter_provider=meter_provider
        )

    def __enter__(self):
        if not self.is_instrumented_by_opentelemetry:
            self.instrument()
        return self

    def __exit__(self):
        if self.is_instrumented_by_opentelemetry:
            self.uninstrument()

    @classmethod
    def from_url(cls, url: str, insecure: bool = True, timeout: Optional[int] = None):
        """
        Construct an instrumentor instance using only the url of the OTLP Collector.
        Inherently modifies the global provider instances adding an export destination
        for the target url.

        .. code-block::

            instrumentor = OtelInstrumentor.from_url("grpc://localhost:4317")

        :param url: Url of the running Otel Collector server. Due to limited support of HTTP protocol
            by the Opentelemetry Python extension, GRPC protocol is preferred.
        :param insecure: Whether non-SSL-protected connection is allowed. Defaults to True.
        :param timeout: Connection timeout in seconds, optional.
        """
        set_logger_destination(OTLPLogExporter(endpoint=url, insecure=insecure, timeout=timeout))
        set_tracer_destination(OTLPSpanExporter(endpoint=url, insecure=insecure, timeout=timeout))
        set_meter_destination(OTLPMetricExporter(endpoint=url, insecure=insecure, timeout=timeout))
        return cls()

    def instrumentation_dependencies(self) -> Collection[str]:
        """
        :meta private:

        Required libraries. Implements the Python Opentelemetry instrumentor interface.

        """
        return INSTRUMENTS

    def _instrument(self, logger_provider=None, tracer_provider=None, meter_provider=None):
        if any([logger_provider, meter_provider, tracer_provider]):
            self._configure_providers(
                logger_provider=logger_provider, tracer_provider=tracer_provider, meter_provider=meter_provider
            )
        for func_name in default_extractors.__all__:
            wrap_function_wrapper(default_extractors, func_name, self.__call__.__wrapped__)

    def _uninstrument(self, **kwargs):
        for func_name in default_extractors.__all__:
            unwrap(default_extractors, func_name)

    def _configure_providers(self, logger_provider, tracer_provider, meter_provider):
        self._logger_provider = logger_provider or get_logger_provider()
        self._tracer_provider = tracer_provider or get_tracer_provider()
        self._meter_provider = meter_provider or get_meter_provider()
        self._logger = get_logger(__name__, None, self._logger_provider)
        self._tracer = get_tracer(__name__, None, self._tracer_provider)
        self._meter = get_meter(__name__, None, self._meter_provider)

    @decorator
    async def __call__(self, wrapped, _, args, kwargs):
        """
        Regular functions that match the :py:class:`~dff.pipeline.types.ExtraHandlerFunction`
        signature can be decorated with the class instance to log the returned value.
        This method implements the logging procedure.
        The returned value is assumed to be `dict` or `NoneType`.
        Logging non-atomic values is discouraged, as they cannot be translated using
        the `Protobuf` protocol.
        Logging is ignored if the application is in 'uninstrumented' state.

        :param wrapped: Function to decorate.
        :param args: Positional arguments of the decorated function.
        :param kwargs: Keyword arguments of the decorated function.
        """
        ctx, _, info = args
        pipeline_component = get_wrapper_field(info)
        attributes = {
            "context_id": str(ctx.id),
            "request_id": get_last_index(ctx.requests),
            "pipeline_component": pipeline_component,
        }

        result: Optional[dict]
        if asyncio.iscoroutinefunction(wrapped):
            result = await wrapped(ctx, _, info)
        else:
            result = wrapped(ctx, _, info)

        if result is None or not self.is_instrumented_by_opentelemetry:
            # self.is_instrumented_by_opentelemetry allows to disable
            # the decorator programmatically if
            # instrumentation is disabled.
            return result

        span: Span
        with self._tracer.start_as_current_span(wrapped.__name__, kind=SpanKind.INTERNAL) as span:
            span_ctx = span.get_span_context()
            record = LogRecord(
                span_id=span_ctx.span_id,
                trace_id=span_ctx.trace_id,
                body=result,
                trace_flags=span_ctx.trace_flags,
                severity_text=None,
                severity_number=SeverityNumber(1),
                resource=resource,
                attributes=attributes,
            )
            self._logger.emit(record=record)
        return result
