from typing import Mapping
from wrapt import wrap_function_wrapper as _wrap
import opentelemetry.exporter.otlp.proto.grpc as otlp_exporter_grpc
from opentelemetry.exporter.otlp.proto.grpc.exporter import _translate_key_values
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValueList


def grpc_mapping_translation_patch(wrapped, _, args, kwargs):
    translated_value = args[0]
    if isinstance(translated_value, Mapping):
        return AnyValue(
            kvlist_value=KeyValueList(values=[_translate_key_values(str(k), v) for k, v in translated_value.items()])
        )
    else:
        wrapped(*args, **kwargs)


_wrap(otlp_exporter_grpc, "exporter._translate_value", grpc_mapping_translation_patch)
