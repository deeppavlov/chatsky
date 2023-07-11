"""
Exporter patch
----------------
This module contains temporary utilities
that patch Opentelemetry's GRPC log exporter
which makes it possible to export arbitrary dict-like values.
"""
from typing import Mapping
from wrapt import wrap_function_wrapper as _wrap
import opentelemetry.exporter.otlp.proto.grpc as otlp_exporter_grpc
from opentelemetry.exporter.otlp.proto.grpc.exporter import _translate_key_values
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValueList


def grpc_mapping_translation_patch(translate_value, _, args, kwargs):
    """
    This decorator patches the `_translate_value` function
    from OpenTelemetry GRPC Log exporter module allowing the class
    to translate values of type `dict` and `NoneType`
    into the `protobuf` protocol.

    :param _translate_value: The original function.
    :param args: Positional arguments of the original function.
    :param kwargs: Keyword arguments of the original function.
    """
    translated_value = args[0]
    if isinstance(translated_value, type(None)):
        return AnyValue(string_value="")
    if isinstance(translated_value, Mapping):
        return AnyValue(
            kvlist_value=KeyValueList(values=[_translate_key_values(str(k), v) for k, v in translated_value.items()])
        )
    else:
        return translate_value(*args, **kwargs)


_wrap(otlp_exporter_grpc, "exporter._translate_value", grpc_mapping_translation_patch)
