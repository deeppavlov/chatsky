from typing import Mapping
from wrapt import wrap_function_wrapper as _wrap
import opentelemetry.exporter.otlp.proto.grpc as otlp_exporter_grpc
from opentelemetry.exporter.otlp.proto.grpc.exporter import _translate_key_values
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValueList
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter


def function(wrapped, _, args, kwargs):
    print('args',args,sep="\t")
    if isinstance(args[0], Mapping) or isinstance(args[0], dict):
        print('\n',"!!!",'\n' )
        return AnyValue(kvlist_value=KeyValueList(values=[_translate_key_values(str(k), v) for k, v in args[1].items()]))
    else:
        wrapped(*args, **kwargs)


_wrap(
    otlp_exporter_grpc,
    "exporter._translate_value",
    function
)

__all__ = [OTLPLogExporter]
