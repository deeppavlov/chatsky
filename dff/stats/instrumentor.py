"""
Instrumentor
-------------
This modules contains the :py:class:`~DFFInstrumentor` class that implements
Opentelemetry's `BaseInstrumentor` interface and allows for automated
instrumentation of Dialog Flow Framework applications,
e.g. for automated logging and log export.

For detailed reference, see `~DFFInstrumentor` class.
"""
import asyncio
from typing import Collection, Optional

from wrapt import wrap_function_wrapper, decorator
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.metrics import get_meter, get_meter_provider, set_meter_provider
from opentelemetry.trace import get_tracer, get_tracer_provider, set_tracer_provider
from opentelemetry._logs import get_logger, get_logger_provider, set_logger_provider
from opentelemetry._logs import SeverityNumber
from opentelemetry.trace import SpanKind, Span
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk.metrics import MeterProvider

from dff.script.core.context import get_last_index
from dff.stats.utils import get_wrapper_field
from dff.stats import defaults


INSTRUMENTS = ["dff"]
SERVICE_NAME = "dialog_flow_framework"

resource = Resource.create({"service.name": SERVICE_NAME})
"""
Singletone :py:class:`~Resource` instance shared inside the framework.
"""

tracer_provider = TracerProvider(resource=resource)
logger_provider = LoggerProvider(resource=resource)
meter_provider = MeterProvider(resource=resource)
set_logger_provider(logger_provider)
set_tracer_provider(tracer_provider)
set_meter_provider(meter_provider)


class DFFInstrumentor(BaseInstrumentor):
    """
    Utility class for instrumenting DFF-related functions
    that implements the :py:class:`~BaseInstrumentor` interface.
    :py:meth:`~instrument` and :py:meth:`~uninstrument` methods
    are available to apply and revert the instrumentation effects.
    Logger provider and tracer provider can be passed to the class
    as keyword arguments;
    otherwise, the global logger provider and tracer provider are leveraged.
    The class implements the :py:meth:`~__call__` method, so that
    regular functions can be decorated using the class instance.

    :param kwargs: you can pass `logger_provider`, `tracer_provider` and `meter_provider`
        parameters to make use of custom instances instead of the globally available.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self._logger_provider = None
        self._tracer_provider = None
        self._meter_provider = None
        self._logger = None
        self._tracer = None
        self._meter = None
        self._configure_providers(**kwargs)

    def instrumentation_dependencies(self) -> Collection[str]:
        return INSTRUMENTS

    def _instrument(self, **kwargs):
        if len(kwargs) > 0:
            self._configure_providers(**kwargs)
        wrap_function_wrapper(defaults, "get_current_label", self.__call__.__wrapped__)
        wrap_function_wrapper(defaults, "get_timing_before", self.__call__.__wrapped__)
        wrap_function_wrapper(defaults, "get_timing_after", self.__call__.__wrapped__)

    def _uninstrument(self, **kwargs):
        unwrap(defaults, "get_current_label")
        unwrap(defaults, "get_timing_before")
        unwrap(defaults, "get_timing_after")

    def _configure_providers(self, **kwargs):
        self._logger_provider = kwargs.get("logger_provider") or get_logger_provider()
        self._tracer_provider = kwargs.get("tracer_provider") or get_tracer_provider()
        self._meter_provider = kwargs.get("meter_provider") or get_meter_provider()
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
