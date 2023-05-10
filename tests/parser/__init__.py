try:
    import pytest

    pytest.register_assert_rewrite("tests.parser.utils")
except ImportError:
    ...
