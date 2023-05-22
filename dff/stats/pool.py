"""
Pool
----
This module defines the :py:class:`.StatsExtractorPool` class.

"""
import functools
import asyncio
from typing import List, Callable, Dict, Optional

from dff.script import Context
from dff.pipeline import ExtraHandlerRuntimeInfo, ExtraHandlerType, ExtraHandlerFunction
from .subscriber import PoolSubscriber
from .record import StatsRecord
from opentelemetry._logs import set_logger_provider, get_logger_provider, get_logger, SeverityNumber
from opentelemetry.trace import get_tracer, SpanKind, get_tracer_provider, set_tracer_provider, Span
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from .exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({"service.name": "basic_service"})
tracer_provider = TracerProvider(resource=resource)
logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)
set_tracer_provider(tracer_provider)
get_logger_provider().add_log_record_processor(
    BatchLogRecordProcessor(OTLPLogExporter(endpoint="grpc://localhost:4317", insecure=True))
)
get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="grpc://localhost:4317", insecure=True))
)


class StatsExtractorPool:
    """
    This class can be used to store sets of wrappers for statistics collection a.k.a. extractors.
    New extractors can be added with the help of the :py:meth:`add_extractor` method.
    These can be accessed by their name and group:

    .. code-block::

        pool[group][extractor.__name__]

    After execution, the result of each extractor will be propagated to subscribers.
    Subscribers should be of type :py:class:`~.PoolSubscriber`.

    When you pass a subscriber instance to the :py:meth:`add_subscriber` method,
        you subscribe it to changes in the given pool.

    :param extractors: You can optionally pass a list of extractors to the class constructor or register
        them later.

    """

    def __init__(self):
        self.subscribers: List[PoolSubscriber] = []
        self._tracer = get_tracer(__name__)
        self._logger = get_logger(__name__)
        self.extractors: Dict[str, Dict[str, ExtraHandlerFunction]] = {}

    def _wrap_extractor(self, extractor: Callable) -> Callable:
        @functools.wraps(extractor)
        async def extractor_wrapper(ctx: Context, _, info: ExtraHandlerRuntimeInfo):
            if asyncio.iscoroutinefunction(extractor):
                result: Optional[StatsRecord] = await extractor(ctx, _, info)
            else:
                result: Optional[StatsRecord] = extractor(ctx, _, info)

            if result is None:
                return result

            span: Span
            with self._tracer.start_as_current_span(f"dff{result.data_key}", kind=SpanKind.INTERNAL) as span:
                span_ctx = span.get_span_context()
                record = LogRecord(
                    observed_timestamp=result.timestamp.timestamp(),
                    span_id=span_ctx.span_id,
                    trace_id=span_ctx.trace_id,
                    body=result.data,
                    trace_flags=span_ctx.trace_flags,
                    severity_text=None,
                    severity_number=SeverityNumber(1),
                    resource=resource,
                    attributes={"context_id": result.context_id, "request_id": result.request_id},
                )
                self._logger.emit(record=record)

            return result

        return extractor_wrapper

    def __getitem__(self, key: ExtraHandlerType):
        return self.extractors[key]

    def add_subscriber(self, subscriber: PoolSubscriber):
        """
        Subscribe a `PoolSubscriber` object to events from this pool.

        :param subscriber: Target subscriber.
        """
        self.subscribers.append(subscriber)

    def add_extractor(self, group: str) -> ExtraHandlerFunction:
        def add_extractor_inner(extractor: Callable):
            """Generic function for adding extractors.
            Requires handler type, e.g. 'before' or 'after'.

            :param extractor: Decorated extractor function.
            :param group: Function execution stage: `before` or `after`.
            """
            wrapped_extractor = self._wrap_extractor(extractor)
            self.extractors[group] = {**self.extractors.get(group, {}), extractor.__name__: wrapped_extractor}
            return self.extractors[group][extractor.__name__]

        return add_extractor_inner

    @property
    def all_handlers(self) -> List[ExtraHandlerFunction]:
        return [item for container in self.extractors.values() for item in container.values()]
