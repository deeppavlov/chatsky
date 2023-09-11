import pytest

try:
    from dff import stats  # noqa: F401
    from opentelemetry.proto.common.v1.common_pb2 import AnyValue
    from opentelemetry.exporter.otlp.proto.grpc.exporter import _translate_value
except ImportError:
    pytest.skip(allow_module_level=True, reason="One of the Opentelemetry packages is missing.")


@pytest.mark.parametrize(
    ["value", "expected_field"], [(1, "int_value"), ({"a": "b"}, "kvlist_value"), (None, "string_value")]
)
def test_body_translation(value, expected_field):
    assert _translate_value.__wrapped__.__name__ == "_translate_value"
    translated_value = _translate_value(value)
    assert isinstance(translated_value, AnyValue)
    assert translated_value.IsInitialized()
    assert getattr(translated_value, expected_field, None) is not None
