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
from opentelemetry.sdk.resources import Resource
from opentelemetry._logs import get_logger_provider, set_logger_provider
from opentelemetry.trace import get_tracer_provider, set_tracer_provider
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter, SpanExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter, LogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter, MetricExporter

from dff.pipeline import ExtraHandlerRuntimeInfo

SERVICE_NAME = "dialog_flow_framework"

resource = Resource.create({"service.name": SERVICE_NAME})
"""
Singletone :py:class:`~Resource` instance shared inside the framework.
"""
tracer_provider = TracerProvider(resource=resource)
"""
Global tracer provider bound to the DFF resource.
"""
logger_provider = LoggerProvider(resource=resource)
"""
Global logger provider bound to the DFF resource.
"""
set_logger_provider(logger_provider)
set_tracer_provider(tracer_provider)


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
    cur_meter_provider = get_meter_provider()
    new_meter_provider = MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(exporter)])
    if not isinstance(cur_meter_provider, MeterProvider):
        set_meter_provider(new_meter_provider)


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
    :param base_url: Base Superset URL.

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


def drop_superset_assets(session: requests.Session, headers: dict, base_url: str):
    """
    Drop the existing assets from the Superset dashboard.

    :param session: Authorized Superset session.
    :param headers: Superset session headers.
    :param base_url: Base Superset URL.
    """
    dashboard_url = parse.urljoin(base_url, "/api/v1/dashboard")
    charts_url = parse.urljoin(base_url, "/api/v1/chart")
    datasets_url = parse.urljoin(base_url, "/api/v1/dataset")
    database_url = parse.urljoin(base_url, "/api/v1/database/")
    delete_res: requests.Response

    dashboard_res = session.get(dashboard_url, headers=headers)
    dashboard_json = dashboard_res.json()
    if dashboard_json["count"] > 0:
        delete_res = requests.delete(dashboard_url, params={"q": json.dumps(dashboard_json["ids"])}, headers=headers)
        delete_res.raise_for_status()

    charts_result = session.get(charts_url, headers=headers)
    charts_json = charts_result.json()
    if charts_json["count"] > 0:
        delete_res = requests.delete(charts_url, params={"q": json.dumps(charts_json["ids"])}, headers=headers)
        delete_res.raise_for_status()

    datasets_result = session.get(datasets_url, headers=headers)
    datasets_json = datasets_result.json()
    if datasets_json["count"] > 0:
        delete_res = requests.delete(datasets_url, params={"q": json.dumps(datasets_json["ids"])}, headers=headers)
        delete_res.raise_for_status()

    database_res = session.get(database_url, headers=headers)
    database_json = database_res.json()
    if database_json["count"] > 0:
        delete_res = requests.delete(database_url + str(database_json["ids"][-1]), headers=headers)
        delete_res.raise_for_status()


class PasswordAction(Action):
    """
    Child class for Argparse's :py:class:`~Action` that prompts users for passwords interactively,
    ensuring password safety, unless the password is specified directly.

    """

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
