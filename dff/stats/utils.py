"""
Utils
-----
This module includes utility functions designed for statistics collection.

The functions below can be used to configure the opentelemetry destination.

.. code:: python

    set_logger_destination(OTLPLogExporter("grpc://localhost:4317", insecure=True))
    set_tracer_destination(OTLPSpanExporter("grpc://localhost:4317", insecure=True))

"""
import json
import getpass
from urllib import parse
from typing import Optional, Tuple
from argparse import Namespace, Action

import requests
from . import exporter_patch  # noqa: F401
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
    """
    Configure the global Opentelemetry logger provider to export logs to the given destination.

    :param exporter: Opentelemetry log exporter instance.
    """
    if exporter is None:
        exporter = OTLPLogExporter(endpoint="grpc://localhost:4317", insecure=True)
    get_logger_provider().add_log_record_processor(BatchLogRecordProcessor(exporter))


def set_meter_destination(exporter: Optional[MetricExporter] = None):
    """
    Configure the global Opentelemetry meter provider to export metrics to the given destination.

    :param exporter: Opentelemetry meter exporter instance.
    """
    if exporter is None:
        exporter = OTLPMetricExporter(endpoint="grpc://localhost:4317", insecure=True)
    get_meter_provider()._all_metric_readers.add(PeriodicExportingMetricReader(exporter))


def set_tracer_destination(exporter: Optional[SpanExporter] = None):
    """
    Configure the global Opentelemetry tracer provider to export traces to the given destination.

    :param exporter: Opentelemetry span exporter instance.
    """
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
    path = info.component.path.replace(".", "-")
    return f"{path}" + (f"-{postfix}" if postfix else "")


def get_superset_session(args: Namespace, base_url: str = "http://localhost:8088/") -> Tuple[requests.Session, dict]:
    """
    Utility function for authorized interaction with Superset HTTP API.

    :param args: Command line arguments including Superset username and Superset password.
    :param base_url: Base superset URL.

    :return: Authorized session - authorization headers tuple.
    """
    healthcheck_url = parse.urljoin(base_url, "/healthcheck")
    login_url = parse.urljoin(base_url, "/api/v1/security/login")
    csrf_url = parse.urljoin(base_url, "/api/v1/security/csrf_token/")

    session = requests.Session()
    # do healthcheck
    response = session.get(healthcheck_url, timeout=10)
    response.raise_for_status()
    # get access token
    access_request = session.post(
        login_url,
        headers={"Content-Type": "application/json", "Accept": "*/*"},
        data=json.dumps({"username": args.username, "password": args.password, "refresh": True, "provider": "db"}),
    )
    access_token = access_request.json()["access_token"]
    # get csrf_token
    csrf_request = session.get(csrf_url, headers={"Authorization": f"Bearer {access_token}"})
    csrf_token = csrf_request.json()["result"]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-CSRFToken": csrf_token,
    }
    return session, headers


class PasswordAction(Action):
    def __init__(
        self, option_strings, dest=None, nargs=0, default=None, required=False, type=None, metavar=None, help=None
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            default=default,
            required=required,
            metavar=metavar,
            type=type,
            help=help,
        )

    def __call__(self, parser, args, values, option_string=None):
        if values:
            print(f"{self.dest}: setting passwords explicitly through the command line is discouraged.")
            setattr(args, self.dest, values)
        else:
            setattr(args, self.dest, getpass.getpass(prompt=f"{self.dest}: "))
